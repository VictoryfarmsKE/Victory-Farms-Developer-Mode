# How to Install ERPNext Version 15 on Ubuntu 22.04 (Linux) — A Step-by-Step Guide

> **Who is this for?** This guide is written in very simple language. If you have never installed a server before, you can still follow it. Think of it like building a Lego house — we do one block at a time.

---

## What are we building?

We are going to install **ERPNext Version 15** on your Windows computer using something called **WSL2**. WSL2 lets you run **Linux** (a type of computer operating system) inside Windows without deleting Windows.

Think of it like this: Windows is your house, and WSL2 is a room inside that house where Linux lives. ERPNext will live inside that room.

---

## How long will this take?

| Step | What we do | Time |
|------|-----------|------|
| Step 1 | Install WSL2 and Ubuntu 22.04 | ~10 minutes |
| Step 2 | Update and prepare Ubuntu | ~15 minutes |
| Step 3 | Create a special user for ERPNext | ~5 minutes |
| Step 4 | Install required tools and software | ~30 minutes |
| Step 5 | Configure the database (MariaDB) | ~10 minutes |
| Step 6 | Install Node.js, NPM, and Yarn | ~15 minutes |
| Step 7 | Install Frappe Bench | ~5 minutes |
| Step 8 | Create the Frappe Bench folder | ~20 minutes |
| Step 9 | Create a new site | ~5 minutes |
| Step 10 | Install ERPNext and other apps | ~20 minutes |
| Step 11 | Start ERPNext | ~2 minutes |
| Step 12 | Set up production mode (optional) | ~15 minutes |
| Step 13 | Install Victory Farms custom app | ~10 minutes |
| | **TOTAL TIME** | **~2.5 to 3 hours** |

> Most of the time is spent waiting for downloads, not doing hard work.

---

## Step 1: Install WSL2 and Ubuntu 22.04

### What are we doing?
We are installing **WSL2** (Windows Subsystem for Linux). This is a tool from Microsoft that lets you run Linux inside Windows.

### Why?
ERPNext is built to run on Linux. WSL2 is the easiest and safest way to get Linux on your Windows computer without deleting Windows or buying a new computer.

### How long does this take?
**About 10 minutes** (plus download time).

### What to do

1. **Press the Windows key** on your keyboard and type `PowerShell`.
2. **Right-click** on "Windows PowerShell" and click **"Run as administrator"**.
3. A blue window will open. Copy and paste this command:

```powershell
wsl --install -d Ubuntu-22.04
```

4. Press **Enter**.
5. Wait. The computer will download and install Ubuntu 22.04.
6. When it finishes, it will ask you to **restart your computer**. Save your work and restart.
7. After restarting, Ubuntu will open automatically and ask you to create a **username** and **password**.
   - Pick any username (for example: `frappe`)
   - Pick a strong password and write it down somewhere safe

> **Common Mistake:** Do not forget your password. You will need it many times. Write it down now.

### What you should see
A message like:
```
Installing: Ubuntu 22.04
Ubuntu 22.04 has been installed.
```

---

## Step 2: Update and Prepare Ubuntu

### What are we doing?
We are making sure Ubuntu is fresh and clean, like updating your phone's apps.

### Why?
An updated system is safer and works better with ERPNext.

### How long does this take?
**About 15 minutes** (mostly waiting).

### What to do

1. You should already be inside the Ubuntu window (black screen with green text).
2. Copy and paste this command:

```bash
sudo apt-get update -y
```

3. Press **Enter**. It will ask for your password. Type it (you will not see anything on screen — this is normal) and press **Enter** again.

4. Then run this:

```bash
sudo apt-get upgrade -y
```

5. Wait for it to finish.

> **Common Mistake:** If you see an error about "permission denied," you probably forgot to type `sudo` at the beginning. `sudo` means "please do this as the boss of the computer."

### What you should see
Many lines scrolling, ending with:
```
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded
```

---

## Step 3: Create a Special User for ERPNext

### What are we doing?
We are creating a new user called `frappe` who will own and run ERPNext.

### Why?
The user you created in Step 1 is like the owner of the house. But we want a separate user (like a manager) whose only job is to run ERPNext. This is safer. The `root` user (the super boss) is too powerful for daily work.

### How long does this take?
**About 5 minutes.**

### What to do

1. Run this to create the new user:

```bash
sudo adduser frappe
```

2. It will ask you to set a password for `frappe`. Type a password and write it down.
3. It will ask for "Full Name" and other things. You can just press **Enter** to skip them.
4. Now give `frappe` the power to use `sudo`:

```bash
sudo usermod -aG sudo frappe
```

5. Switch to the `frappe` user:

```bash
su - frappe
```

6. You should now see something like `frappe@your-computer-name:~$`

### What you should see
```
Adding user 'frappe' ...
Adding new group 'frappe' (1001) ...
Adding new user 'frappe' (1001) with group 'frappe' ...
```

---

## Step 4: Install Required Tools and Software

### What are we doing?
We are installing all the helper programs that ERPNext needs to run.

### Why?
ERPNext is like a big car. Before the car can drive, you need fuel, oil, wheels, and keys. These programs are the fuel, oil, wheels, and keys for ERPNext.

### How long does this take?
**About 30 minutes** (mostly downloading).

### What to do

**Make sure you are still the `frappe` user.** If not, run `su - frappe` first.

#### 4a. Install Git
Git is a tool that downloads code from the internet.

```bash
sudo apt-get install git -y
```

#### 4b. Install Python 3.10+
ERPNext is written in a language called Python. Version 15 needs Python 3.10 or newer.

```bash
sudo apt-get install python3-dev python3.10-dev python3-setuptools python3-pip python3-distutils -y
```

#### 4c. Install Python Virtual Environment
A virtual environment is like a separate toy box. It keeps ERPNext's toys separate from the rest of the computer's toys.

```bash
sudo apt-get install python3.10-venv -y
```

#### 4d. Install Software Properties Common
This helps manage software sources.

```bash
sudo apt-get install software-properties-common -y
```

#### 4e. Install MariaDB (the database)
ERPNext stores all your data (customers, sales, stock) in a database called MariaDB. Think of MariaDB like a very smart Excel file that never crashes.

```bash
sudo apt install mariadb-server mariadb-client -y
```

#### 4f. Install Redis
Redis is a super-fast memory helper. ERPNext uses it for things like "who is logged in" and "what jobs need to run in the background."

```bash
sudo apt-get install redis-server -y
```

#### 4g. Install PDF and Font Tools
ERPNext makes PDFs (like invoices and reports). These tools help with that.

```bash
sudo apt-get install xvfb libfontconfig wkhtmltopdf -y
sudo apt-get install libmysqlclient-dev -y
```

> **Common Mistake:** If a command says "unable to locate package," try running `sudo apt-get update` again and then retry.

### What you should see
Each command should end with lines like:
```
0 upgraded, X newly installed, 0 to remove and 0 not upgraded
```

---

## Step 5: Configure MariaDB (the Database)

### What are we doing?
We are setting up the database securely and telling it how to read and write text.

### Why?
The database needs a strong password and special settings so ERPNext can store words in any language (including Swahili and emojis!).

### How long does this take?
**About 10 minutes.**

### What to do

#### 5a. Secure the database
Run this command:

```bash
sudo mysql_secure_installation
```

You will see a series of questions. Answer them exactly like this:

| Question | Your Answer |
|----------|-------------|
| Enter current password for root | Press **Enter** (there is no password yet) |
| Switch to unix_socket authentication? | Type `Y` and press **Enter** |
| Change the root password? | Type `Y` and press **Enter** |
| New password | Choose a strong password and **write it down** |
| Re-enter new password | Type it again |
| Remove anonymous users? | Type `Y` and press **Enter** |
| Disallow root login remotely? | Type `N` and press **Enter** (you may want to connect from tools like Power BI later) |
| Remove test database? | Type `Y` and press **Enter** |
| Reload privilege tables now? | Type `Y` and press **Enter** |

#### 5b. Edit the database config file
Run this:

```bash
sudo nano /etc/mysql/my.cnf
```

A text editor will open. Use your arrow keys to go to the bottom. Copy and paste this exact block:

```
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
```

To save and exit:
- Press `Ctrl + O` (the letter O), then **Enter** to save
- Press `Ctrl + X` to exit

#### 5c. Restart the database

```bash
sudo service mysql restart
```

### What you should see
After restarting, no error message means it worked.

---

## Step 6: Install Node.js, NPM, and Yarn

### What are we doing?
We are installing Node.js, which builds and runs the pretty web pages you see in ERPNext.

### Why?
ERPNext has two parts: the brain (Python) and the face (JavaScript/Node). Node makes the face look good and work fast.

### How long does this take?
**About 15 minutes**.

### What to do

#### 6a. Install CURL
CURL is a tool that downloads things from the internet.

```bash
sudo apt install curl -y
```

#### 6b. Install Node.js using NVM
NVM is a tool that helps you pick the right version of Node. ERPNext v15 needs Node 18.

```bash
curl https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash
```

Now reload your settings:

```bash
source ~/.profile
```

Install Node 18:

```bash
nvm install 18
```

Check that it worked:

```bash
node -v
```

You should see `v18.x.x` (where x.x are numbers).

#### 6c. Install NPM
NPM comes with Node, but let's make sure:

```bash
sudo apt-get install npm -y
```

#### 6d. Install Yarn
Yarn is a helper that manages JavaScript packages.

```bash
sudo npm install -g yarn
```

### What you should see
```
v18.20.0
```
(or another version starting with 18)

---

## Step 7: Install Frappe Bench

### What are we doing?
We are installing **Bench**, which is the manager or helper tool for ERPNext.

### Why?
Bench does all the hard work for you. It creates sites, installs apps, starts the server, and updates things. Without Bench, you would have to do all of that manually.

### How long does this take?
**About 5 minutes**.

### What to do

```bash
sudo pip3 install frappe-bench
```

### What you should see
Many lines ending with:
```
Successfully installed frappe-bench
```

---

## Step 8: Create the Frappe Bench Folder

### What are we doing?
We are downloading the **Frappe Framework** — the foundation that ERPNext sits on top of.

### Why?
Think of Frappe as the concrete foundation of a house, and ERPNext as the house built on top of it. You cannot build the house without the foundation.

### How long does this take?
**About 20 minutes** (downloading code).

### What to do

```bash
bench init --frappe-branch version-15 frappe-bench
```

Wait. This downloads a lot of code.

### What you should see
```
SUCCESS: Bench frappe-bench initialized
```

---

## Step 9: Create a New Site

### What are we doing?
We are creating a "site" — one company or one instance of ERPNext.

### Why?
ERPNext can run many companies on one computer. Each company is a "site." We are creating your first site.

### How long does this take?
**About 5 minutes**.

### What to do

1. Go inside the bench folder:

```bash
cd frappe-bench
```

2. Create your site. You can name it anything, like `victoryfarms.local`:

```bash
bench new-site victoryfarms.local
```

3. It will ask for the **MariaDB root password** (the one you set in Step 5a). Type it and press **Enter**.

> **Common Mistake:** If it says "Access denied," you typed the wrong MariaDB password. Try again.

### What you should see
```
Installing frappe...
*** Scheduler is disabled ***
Current Site set to victoryfarms.local
```

---

## Step 10: Install ERPNext and Other Apps

### What are we doing?
We are downloading ERPNext and any extra apps (like HRMS) and installing them on your site.

### Why?
Right now you only have the empty foundation (Frappe). Now we are building the actual ERPNext house on top of it.

### How long does this take?
**About 20 minutes**.

### What to do

#### 10a. Download the Payments app
ERPNext needs this to handle money.

```bash
bench get-app payments
```

#### 10b. Download ERPNext v15

```bash
bench get-app --branch version-15 erpnext
```

#### 10c. Download HRMS (Human Resources) — optional but recommended

```bash
bench get-app hrms
```

#### 10d. Install everything on your site

```bash
bench --site victoryfarms.local install-app erpnext
```

Wait for it to finish. Then install HRMS:

```bash
bench --site victoryfarms.local install-app hrms
```

### What you should see
```
Installing erpnext...
Updating Dashboard for erpnext
```

---

## Step 11: Start ERPNext

### What are we doing?
We are turning on the engine. ERPNext will now run on your computer.

### Why?
Until now, everything was just files sitting on the computer. Now we are starting the program so you can use it in your web browser.

### How long does this take?
**About 2 minutes**.

### What to do

Make sure you are inside `frappe-bench` and run:

```bash
bench start
```

### What you should see
Many lines of text, and at the bottom something like:
```
17:28:12 web.1      |  * Running on http://0.0.0.0:8000
```

### How to use it
1. Open your web browser (Chrome, Edge, Firefox).
2. Go to: `http://localhost:8000`
3. You should see the ERPNext login page!

> **Important:** While `bench start` is running, the black Ubuntu window must stay open. If you close it, ERPNext stops. Later we will learn how to make it run automatically.

---

## Step 12: Set Up Production Mode (Optional but Recommended)

### What are we doing?
We are telling the computer: "Start ERPNext automatically every time I turn on the computer."

### Why?
Right now, if you restart your computer, ERPNext will not start by itself. You would have to open Ubuntu and type `bench start` every time. Production mode fixes that.

### How long does this take?
**About 15 minutes**.

### What to do

Make sure you are inside `frappe-bench`.

#### 12a. Enable the scheduler
The scheduler is like an alarm clock for ERPNext. It reminds ERPNext to do background jobs.

```bash
bench --site victoryfarms.local enable-scheduler
```

#### 12b. Turn off maintenance mode

```bash
bench --site victoryfarms.local set-maintenance-mode off
```

#### 12c. Set up production config
Replace `frappe` with your Linux username (if you used a different one):

```bash
sudo bench setup production frappe
```

#### 12d. Set up NGINX
NGINX is like a traffic police officer. It directs web visitors to ERPNext.

```bash
bench setup nginx
```

#### 12e. Restart everything

```bash
sudo supervisorctl restart all
```

Then run the production setup one more time:

```bash
sudo bench setup production frappe
```

If it asks you to save a config file, type `Y` and press **Enter**.

### What you should see
```
Restarting supervisor workers...
```

Now ERPNext will start automatically when you restart your computer. You can access it at `http://localhost` (no port needed) or `http://[your-computer-IP]`.

> **Note:** In production mode, `bench start` is no longer needed. The computer handles it.

---

## Step 13: Install the Victory Farms Custom App

### What are we doing?
We are adding your company's custom changes (custom scripts, notifications, and fields) on top of ERPNext.

### Why?
ERPNext is a general system for all companies. Your `Victory-Farms-Developer-Mode` app adds special features and rules that only Victory Farms needs.

### How long does this take?
**About 10 minutes**.

### What to do

Make sure you are inside `frappe-bench`.

#### 13a. Copy your app folder into the bench
You need to copy your `Victory-Farms-Developer-Mode` folder into the `apps` folder inside `frappe-bench`.

If your folder is on Windows (for example, on your Desktop), run this from inside Ubuntu:

```bash
cp -r /mnt/c/Users/VF6988/OneDrive\ -\ Victory\ Farms\ Ltd/Desktop/Victory-Farms-Developer-Mode apps/victoryfarmsdeveloper
```

> **Tip:** If the path looks scary, you can also open File Explorer in Windows, go to your `Victory-Farms-Developer-Mode` folder, copy it, and paste it into:
> `\\wsl.localhost\Ubuntu-22.04\home\frappe\frappe-bench\apps\`
> Then rename the pasted folder to `victoryfarmsdeveloper`.

#### 13b. Install the app on your site

```bash
bench --site victoryfarms.local install-app victoryfarmsdeveloper
```

#### 13c. Restart the bench

```bash
bench restart
```

### What you should see
```
Installing victoryfarmsdeveloper...
Updating Dashboard for victoryfarmsdeveloper
```

---

## You Are Done!

If you followed all the steps, you now have:

- **ERPNext Version 15** running on your computer
- **WSL2 + Ubuntu 22.04** installed
- **Your Victory Farms custom app** installed

### How to open ERPNext
- **Development mode:** Open browser, go to `http://localhost:8000`
- **Production mode:** Open browser, go to `http://localhost`

### Default login
- **Username:** `Administrator`
- **Password:** The MariaDB root password you set in Step 5a

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Permission denied" | Did you forget `sudo`? Or are you not the `frappe` user? |
| "Command not found" | Did you forget to install that tool in Step 4? |
| "Access denied for MariaDB" | You typed the wrong MariaDB password. Reset it or try again. |
| "Port 8000 already in use" | Another program is using that port. Restart your computer or change the port. |
| ERPNext does not start after reboot | Did you complete Step 12 (Production mode)? |

---

## Need Help?

If you get stuck on any step, read the "Common Mistake" box under that step. Most errors are caused by:
1. Forgetting to type `sudo`
2. Typing the wrong password
3. Skipping a step

Go back, read the step again carefully, and try once more.

---

*Good luck, and welcome to ERPNext!*
