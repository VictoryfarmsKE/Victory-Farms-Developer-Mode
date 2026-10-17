import contextlib
from datetime import timedelta

import frappe
from frappe.utils import add_months, get_datetime, get_first_day, get_last_day, getdate, now_datetime

DOCTYPE = "VF GL Day Total"
TABLE = f"tab{DOCTYPE}"
MARK_KEY = "vf_gl_day_totals_mark"
LATE_COMMIT_ALLOWANCE = timedelta(hours=3)
BUILD_JOB_ID = "vf_gl_day_totals_build"
VERIFY_JOB_ID = "vf_gl_day_totals_verify"
LOCK_NAME = "vf_gl_day_totals"
DAYS_PER_CHUNK = 7
INSERT_CHUNK = 5000
TOTAL_FIELDS = (
	"company",
	"posting_date",
	"account",
	"cost_center",
	"finance_book",
	"is_opening",
	"is_closing",
	"fiscal_year",
	"account_currency",
	"debit",
	"credit",
	"debit_in_account_currency",
	"credit_in_account_currency",
	"entries",
)
GROUPED_GL_SELECT = """
	SELECT
		company,
		posting_date,
		IFNULL(account, '') AS account,
		IFNULL(cost_center, '') AS cost_center,
		IFNULL(finance_book, '') AS finance_book,
		IFNULL(is_opening, '') AS is_opening,
		IF(voucher_type IS NULL OR voucher_type = 'Period Closing Voucher', 1, 0) AS is_closing,
		IFNULL(fiscal_year, '') AS fiscal_year,
		IFNULL(account_currency, '') AS account_currency,
		SUM(debit),
		SUM(credit),
		SUM(debit_in_account_currency),
		SUM(credit_in_account_currency),
		COUNT(*)
	FROM `tabGL Entry`
	WHERE is_cancelled = 0 AND company IS NOT NULL AND {condition}
	GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
"""


def ensure_table():
	frappe.db.sql_ddl(
		f"""
		CREATE TABLE IF NOT EXISTS `{TABLE}` (
			company varchar(140) NOT NULL,
			posting_date date NOT NULL,
			account varchar(140) NOT NULL DEFAULT '',
			cost_center varchar(140) NOT NULL DEFAULT '',
			finance_book varchar(140) NOT NULL DEFAULT '',
			is_opening varchar(140) NOT NULL DEFAULT '',
			is_closing tinyint NOT NULL DEFAULT 0,
			fiscal_year varchar(140) NOT NULL DEFAULT '',
			account_currency varchar(140) NOT NULL DEFAULT '',
			debit decimal(21,9) NOT NULL DEFAULT 0,
			credit decimal(21,9) NOT NULL DEFAULT 0,
			debit_in_account_currency decimal(21,9) NOT NULL DEFAULT 0,
			credit_in_account_currency decimal(21,9) NOT NULL DEFAULT 0,
			entries int NOT NULL DEFAULT 0,
			KEY company_date_account (company, posting_date, account),
			KEY posting_date (posting_date)
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
		"""
	)


def get_mark():
	value = frappe.db.get_global(MARK_KEY)
	return get_datetime(value) if value else None


def set_mark(value):
	frappe.db.set_global(MARK_KEY, str(value))


def is_ready():
	return bool(get_mark()) and frappe.db.table_exists(DOCTYPE)


def live_dates(company):
	mark = get_mark()
	if not mark:
		return None
	return set(
		frappe.db.sql_list(
			"""
			SELECT DISTINCT posting_date FROM `tabGL Entry`
			WHERE modified >= %s AND company = %s AND posting_date IS NOT NULL
			""",
			(mark - LATE_COMMIT_ALLOWANCE, company),
		)
	)


@contextlib.contextmanager
def write_lock(wait_seconds=0):
	name = f"{frappe.conf.db_name}:{LOCK_NAME}"
	acquired = frappe.db.sql("SELECT GET_LOCK(%s, %s)", (name, wait_seconds))[0][0] == 1
	try:
		yield acquired
	finally:
		if acquired:
			frappe.db.sql("SELECT RELEASE_LOCK(%s)", (name,))


def rebuild_range(from_date, to_date):
	rows = frappe.db.sql(
		GROUPED_GL_SELECT.format(condition="posting_date BETWEEN %(from_date)s AND %(to_date)s"),
		{"from_date": from_date, "to_date": to_date},
	)
	frappe.db.sql(
		f"DELETE FROM `{TABLE}` WHERE posting_date BETWEEN %s AND %s",
		(from_date, to_date),
	)
	insert_rows(rows)


def rebuild_dates(dates):
	dates = sorted(set(dates))
	for start in range(0, len(dates), DAYS_PER_CHUNK):
		chunk = dates[start : start + DAYS_PER_CHUNK]
		rows = frappe.db.sql(
			GROUPED_GL_SELECT.format(condition="posting_date IN %(dates)s"),
			{"dates": tuple(chunk)},
		)
		frappe.db.sql(f"DELETE FROM `{TABLE}` WHERE posting_date IN %s", (tuple(chunk),))
		insert_rows(rows)
		frappe.db.commit()


def insert_rows(rows):
	if rows:
		frappe.db.bulk_insert(DOCTYPE, TOTAL_FIELDS, rows, chunk_size=INSERT_CHUNK)


def months_between(first_date, last_date):
	month_start = get_first_day(first_date)
	while month_start <= last_date:
		yield month_start, get_last_day(month_start)
		month_start = add_months(month_start, 1)


def build():
	ensure_table()
	with write_lock(wait_seconds=600) as acquired:
		if not acquired:
			return
		started = now_datetime()
		bounds = frappe.db.sql(
			"SELECT MIN(posting_date), MAX(posting_date) FROM `tabGL Entry` WHERE is_cancelled = 0"
		)[0]
		if bounds[0]:
			frappe.db.sql(f"DELETE FROM `{TABLE}` WHERE posting_date < %s OR posting_date > %s", bounds)
			for month_start, month_end in months_between(getdate(bounds[0]), getdate(bounds[1])):
				rebuild_range(month_start, month_end)
				frappe.db.commit()
		set_mark(started)
		frappe.db.commit()


def enqueue_build():
	frappe.enqueue(
		"victoryfarmsdeveloper.setup.gl_day_totals.build",
		queue="long",
		timeout=7200,
		job_id=BUILD_JOB_ID,
		deduplicate=True,
	)


def refresh():
	if not frappe.db.table_exists(DOCTYPE):
		return
	mark = get_mark()
	if not mark:
		enqueue_build()
		return
	with write_lock() as acquired:
		if not acquired:
			return
		started = now_datetime()
		settled_dates = frappe.db.sql_list(
			"""
			SELECT DISTINCT posting_date FROM `tabGL Entry`
			WHERE modified >= %s AND modified < %s AND posting_date IS NOT NULL
			""",
			(mark - LATE_COMMIT_ALLOWANCE, started - LATE_COMMIT_ALLOWANCE),
		)
		rebuild_dates(settled_dates)
		set_mark(started)
		frappe.db.commit()


def enqueue_verify():
	if not get_mark():
		return
	frappe.enqueue(
		"victoryfarmsdeveloper.setup.gl_day_totals.verify",
		queue="long",
		timeout=7200,
		job_id=VERIFY_JOB_ID,
		deduplicate=True,
	)


def verify(from_date=None):
	if not get_mark():
		return []
	from_date = getdate(from_date) if from_date else getdate(f"{getdate().year - 1}-01-01")
	with write_lock(wait_seconds=600) as acquired:
		if not acquired:
			return []
		live = live_dates_all()
		wrong_dates = []
		for month_start, month_end in months_between(from_date, getdate()):
			wrong_dates.extend(d for d in mismatched_dates(month_start, month_end) if d not in live)
		rebuild_dates(wrong_dates)
		if wrong_dates:
			frappe.log_error(
				title="GL day totals repaired",
				message="\n".join(str(d) for d in sorted(wrong_dates)),
			)
		return wrong_dates


def live_dates_all():
	return set(
		frappe.db.sql_list(
			"SELECT DISTINCT posting_date FROM `tabGL Entry` WHERE modified >= %s AND posting_date IS NOT NULL",
			(get_mark() - LATE_COMMIT_ALLOWANCE,),
		)
	)


def mismatched_dates(from_date, to_date):
	ledger = day_sums(
		"""
		SELECT company, posting_date, COUNT(*), SUM(debit), SUM(credit)
		FROM `tabGL Entry`
		WHERE is_cancelled = 0 AND company IS NOT NULL AND posting_date BETWEEN %s AND %s
		GROUP BY 1, 2
		""",
		from_date,
		to_date,
	)
	totals = day_sums(
		f"""
		SELECT company, posting_date, SUM(entries), SUM(debit), SUM(credit)
		FROM `{TABLE}`
		WHERE posting_date BETWEEN %s AND %s
		GROUP BY 1, 2
		""",
		from_date,
		to_date,
	)
	return sorted({key[1] for key in ledger.keys() | totals.keys() if ledger.get(key) != totals.get(key)})


def day_sums(query, from_date, to_date):
	return {(row[0], row[1]): tuple(row[2:]) for row in frappe.db.sql(query, (from_date, to_date))}
