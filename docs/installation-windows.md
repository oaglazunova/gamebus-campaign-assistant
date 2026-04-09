# Installation on Windows

This guide explains how to install and start **GameBus Campaign Assistant** on a Windows computer.

## Before you begin

You need:

- a Windows computer
- permission to install software
- internet access during installation

## Step 1 — Install Python

GameBus Campaign Assistant needs Python to run.

### What to do

1. Go to the Python website
2. Download **Python 3.11** or newer
3. Run the installer

### Important
During installation, make sure you enable:

- **Add Python to PATH**

This option is very important.

## Step 2 — Download or unzip the project

You should now have a folder containing files such as:

- `README.md`
- `pyproject.toml`
- `src`
- `docs`
- `scripts`

If the project came as a ZIP file:

1. Right-click the ZIP file
2. Choose **Extract All...**
3. Open the extracted folder

## Step 3 — Install the app

### Easiest way

If your copy of the project contains:

- `scripts/install_windows.bat`

then simply:

1. open the `scripts` folder
2. double-click `install_windows.bat`

A terminal window may appear for a few minutes. This is normal.

When installation is complete, you should see a success message.

### What the installer does
It usually:

- creates a local virtual environment
- installs the required Python packages

## Step 4 — Start the app

If your copy of the project contains:

- `scripts/run_app.bat`

then:

1. open the `scripts` folder
2. double-click `run_app.bat`

Your browser should open automatically.

If it does not, check the terminal window for a local address such as:

- `http://localhost:8501`

and open it in your browser.

---

# Manual installation (only if needed)

Use this only if the batch files are not available or do not work.

## 1. Open a terminal in the project folder

The easiest way is:

1. open the project folder in File Explorer
2. click in the address bar
3. type `cmd`
4. press Enter

A terminal window should open in that folder.

## 2. Create a virtual environment

```powershell
python -m venv .venv
````

## 3. Activate it

```powershell id="j7r27m"
.venv\Scripts\activate
```

## 4. Install the app

```powershell id="0lwx6d"
pip install -e .
```

## 5. Start the app

```powershell id="x3umnd"
streamlit run src/campaign_assistant/app.py
```

After a short moment, Streamlit should show a local address and the app should open in your browser.

---

# First start: what you should see

When the app opens, you should see:

* a sidebar on the left
* a title at the top
* options to upload a campaign file or download one from GameBus
* an **Analyze campaign** button

If you see this, the installation worked.

---

# If Windows shows a warning

Sometimes Windows warns about scripts or downloaded files.

Possible examples:

* “Windows protected your PC”
* PowerShell execution warnings
* SmartScreen warning

If you are using files from a trusted internal source, you may need to:

* choose **More info**
* then choose **Run anyway**

If you are unsure, ask the person who gave you the tool.

---

# Troubleshooting

## Problem: `python` is not recognized

This usually means Python was installed without enabling **Add Python to PATH**.

### Fix

Reinstall Python and make sure that option is checked.

---

## Problem: nothing happens when I double-click the script

Possible causes:

* Python is not installed
* the installation did not finish correctly
* your system blocks `.bat` scripts

### Try this

1. open the `scripts` folder
2. right-click the script
3. choose **Open**
4. or run the manual installation commands

---

## Problem: the browser does not open automatically

Sometimes the app starts but does not open the browser.

### Fix

Look at the terminal window and find a line like:

* `Local URL: http://localhost:8501`

Copy that address into your browser.

---

## Problem: installation fails while downloading packages

This may happen because of:

* no internet connection
* restricted network
* temporary package server issue

### Fix

Try again later, or ask your IT support whether Python package downloads are allowed.

---

## Problem: I closed the terminal and the app stopped

This is expected.

The app runs only while the terminal window is open.

### Fix

Start it again using:

* `scripts/run_app.bat`
  or
* the manual Streamlit command

---

# Updating the app

If you receive a newer version of the project:

1. replace the old project folder with the new one
2. run `install_windows.bat` again if instructed
3. start the app normally

---

# Where local files are stored

The app may store local settings such as:

* remembered email
* saved campaign abbreviations
* session cookies

These are stored locally on your Windows computer.

Passwords, if remembered, are stored using the Windows keyring system rather than in plain text.

---

# Need help?

If the app still does not start, check:

* `README.md`
* `docs/user-guide.md`

If needed, contact the person who shared the tool with you.
