# Installation on Windows

This guide explains how to install and start **GameBus Campaign Assistant** on a Windows computer.

## Before you begin

You need:

- a Windows computer
- permission to install software
- internet access during installation

Ollama is optional. The deterministic campaign checks work without Ollama. Ollama is only needed if you want the **Assistant** tab to provide richer local explanations via an LLM.

## Step 1 - Install Python

GameBus Campaign Assistant needs Python to run.

### What to do

1. Go to the Python website: https://www.python.org/downloads/
2. Download **Python 3.14** or newer
3. Run the installer

### Important

During installation, make sure you enable:

- **Add Python to PATH**

This option is very important.

## Step 2 - Download or unzip the project

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

## Step 3 - Install the app

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

## Step 4 - Optional: Install Ollama for Assistant explanations

GameBus Campaign Assistant can run deterministic checks without Ollama.

Ollama is only needed if you want the **Assistant** tab to provide richer local explanations.

### What Ollama does

Ollama runs a local language model on your computer.

This means:

- campaign explanations can be generated locally
- no public LLM API is needed
- the deterministic checks still work even if Ollama is not installed

### 4.1 Install Ollama

1. Go to the Ollama website: https://ollama.com/download
2. Download Ollama for Windows
3. Run the installer
4. After installation, restart your terminal if it was already open

Ollama may run in the background after installation.

### 4.2 Install the recommended model

Open a terminal and run:

```powershell
ollama pull gemma3:1b
```

This downloads the default lightweight model used by the app.

The download may take some time.

### 4.3 Check that the model is installed

Run:

```powershell
ollama list
```

You should see something like:

```text
gemma3:1b
```

### 4.4 Test the model

Run:

```powershell
ollama run gemma3:1b
```

If the model starts and you can type a message, Ollama is working.

To leave the model chat, type:

```text
/bye
```

or press:

```text
Ctrl + D
```

### 4.5 Start Ollama manually if needed

Usually Ollama starts automatically.

If the Assistant says that Ollama is unavailable, open a terminal and run:

```powershell
ollama serve
```

Keep that terminal window open, then start the GameBus Campaign Assistant in another terminal or using `run_app.bat`.

### 4.6 Switch to another Ollama model

You can use another model if it is installed locally.

First download the model, for example:

```powershell
ollama pull llama3.2:3b
```

Then start the app with that model.

#### Temporary switch for the current terminal

Use this if you start the app manually from PowerShell:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_MODEL="llama3.2:3b"
python -m streamlit run src/campaign_assistant/app.py
```

This setting only applies to the current terminal window.

#### Persistent switch for future terminals

Use this if you want Windows to remember the selected model:

```powershell
setx CAMPAIGN_ASSISTANT_LLM_MODEL "llama3.2:3b"
```

After running `setx`, close the terminal and open a new one.

Then start the app normally.

### 4.7 Switch back to the default model

To switch back temporarily:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_MODEL="gemma3:1b"
python -m streamlit run src/campaign_assistant/app.py
```

To switch back persistently:

```powershell
setx CAMPAIGN_ASSISTANT_LLM_MODEL "gemma3:1b"
```

Then close and reopen the terminal.

### 4.8 Disable LLM support

If you do not want to use Ollama, you can disable LLM support.

Temporary setting:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_ENABLED="false"
python -m streamlit run src/campaign_assistant/app.py
```

Persistent setting:

```powershell
setx CAMPAIGN_ASSISTANT_LLM_ENABLED "false"
```

To enable it again:

```powershell
setx CAMPAIGN_ASSISTANT_LLM_ENABLED "true"
```

Then close and reopen the terminal.

### 4.9 Recommended models

For most users, start with:

```text
gemma3:1b
```

This is small and usually faster on normal laptops.

If your computer is powerful enough, you can try a larger model, for example:

```text
llama3.2:3b
```

Larger models may give better explanations, but they are slower and require more memory and disk space.

## Step 5 — Start the app

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

# Manual installation only if needed

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
```

## 3. Activate it

```powershell
.venv\Scripts\activate
```

## 4. Install the app

```powershell
python -m pip install -e .
```

## 5. Start the app

```powershell
python -m streamlit run src/campaign_assistant/app.py
```

After a short moment, Streamlit should show a local address and the app should open in your browser.

---

# First start: what you should see

When the app opens, you should see:

- a sidebar on the left
- a title at the top
- options to upload a campaign file or download one from GameBus
- an **Analyze campaign** button

If you see this, the installation worked.

---

# If Windows shows a warning

Sometimes Windows warns about scripts or downloaded files.

Possible examples:

- “Windows protected your PC”
- PowerShell execution warnings
- SmartScreen warning

If you are using files from a trusted internal source, you may need to:

- choose **More info**
- then choose **Run anyway**

If you are unsure, ask the person who gave you the tool.

---

# Troubleshooting

## Problem: `python` is not recognized

This usually means Python was installed without enabling **Add Python to PATH**.

### Fix

Reinstall Python and make sure that option is checked.

---

## Problem: `ModuleNotFoundError: No module named 'campaign_assistant'`

This usually means the app was started before the package was installed into the active Python environment.

### Fix

Open a terminal in the project folder and run:

```powershell
python -m pip install -e .
python -m streamlit run src/campaign_assistant/app.py
```

Make sure you run these commands from the project folder, where `pyproject.toml` is located.

---

## Problem: nothing happens when I double-click the script

Possible causes:

- Python is not installed
- the installation did not finish correctly
- your system blocks `.bat` scripts

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

- `Local URL: http://localhost:8501`

Copy that address into your browser.

---

## Problem: installation fails while downloading packages

This may happen because of:

- no internet connection
- restricted network
- temporary package server issue

### Fix

Try again later, or ask your IT support whether Python package downloads are allowed.

---

## Problem: Assistant says Ollama is unavailable

The deterministic checks still work, but the Assistant cannot use the local LLM.

### Possible causes

- Ollama is not installed
- Ollama is not running
- the selected model has not been downloaded
- the selected model name is different from the installed model name

### Fix

Check whether Ollama is installed:

```powershell
ollama list
```

If this command does not work, install Ollama first.

If Ollama is installed but the model is missing, run:

```powershell
ollama pull gemma3:1b
```

If Ollama is installed but not running, run:

```powershell
ollama serve
```

Then start the app again.

---

## Problem: Ollama says the model was not found

This means the app is configured to use a model that is not installed locally.

### Fix

Install the default model:

```powershell
ollama pull gemma3:1b
```

Or switch the app to a model that you already have:

```powershell
ollama list
```

Then set the model name, for example:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_MODEL="llama3.2:3b"
python -m streamlit run src/campaign_assistant/app.py
```

---

## Problem: Ollama is too slow

Local models depend on your computer.

### Try this

Use the smaller default model:

```powershell
ollama pull gemma3:1b
$env:CAMPAIGN_ASSISTANT_LLM_MODEL="gemma3:1b"
python -m streamlit run src/campaign_assistant/app.py
```

You can also disable LLM support completely:

```powershell
$env:CAMPAIGN_ASSISTANT_LLM_ENABLED="false"
python -m streamlit run src/campaign_assistant/app.py
```

The deterministic campaign checks will still work.

---

## Problem: I closed the terminal and the app stopped

This is expected.

The app runs only while the terminal window is open.

### Fix

Start it again using:

- `scripts/run_app.bat`
- or the manual Streamlit command

---

# Updating the app

If you receive a newer version of the project:

1. replace the old project folder with the new one
2. run `install_windows.bat` again if instructed
3. start the app normally

---

# Where local files are stored

The app may store local settings such as:

- remembered email
- saved campaign abbreviations
- session cookies

These are stored locally on your Windows computer.

Passwords, if remembered, are stored using the Windows keyring system rather than in plain text.

---

# Need help?

If the app still does not start, check:

- `README.md`
- `docs/user_guide.md`

If needed, contact the person who shared the tool with you.
