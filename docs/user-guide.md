# User Guide

This guide explains how to use **GameBus Campaign Assistant** to check a GameBus campaign Excel export.

## What this app is for

GameBus Campaign Assistant helps you inspect a campaign configuration file that was exported from GameBus.

It can help you:

- run the existing campaign checks,
- see which checks passed or failed,
- read issues in a chat-style interface,
- understand TTM-related problems,
- and optionally download an Excel error report.

## What you need before starting

Before you use the app, make sure you have:

- a GameBus campaign Excel export (`.xlsx`), or
- valid GameBus credentials if you use the optional download feature

If you are not sure, the safest workflow is:

1. export the campaign from GameBus manually
2. save the `.xlsx` file on your computer
3. upload it in the app

## Starting the app

### If you received the Windows scripts

1. Open the project folder
2. Double-click `scripts/run_app.bat`
3. Wait for your browser to open

### If you start it manually

Open a terminal in the project folder and run:

```powershell
streamlit run src/campaign_assistant/app.py
````

After a short moment, the app should open in your browser.

---

# Checking a campaign

## Option 1 — Upload a campaign Excel file

This is the easiest and most reliable method.

1. Open the app
2. In the sidebar, choose **Upload Excel file**
3. Click the upload field
4. Select your campaign `.xlsx` file
5. Choose the checks you want to run
6. Click **Analyze campaign**

The assistant will then show a summary in the main panel.

## Option 2 — Download from GameBus

If this feature is available in your version of the app:

1. Open the app
2. In the sidebar, choose **Download from GameBus**
3. Enter your email and password
4. Enter the campaign abbreviation
5. Click **Analyze campaign**

The app will try to download the campaign file first, and then run the checks.

If this does not work, use **Option 1** instead.

---

# Understanding the results

After analysis, the assistant will show:

* the number of issues found,
* which checks failed,
* which checks passed,
* and which waves are active now, if available in the file.

Below that, you will see issues grouped by **check type**.

Examples:

* Reachability
* Consistency
* Visualization internals
* Target points reachable
* Secrets
* TTM structure

## What “priority” means

The assistant tries to show the most important issues first.

At the moment, priority is based mainly on:

* issue severity
* whether the issue belongs to an active wave

This means that a serious issue in an active wave is usually shown before a less important issue in an inactive wave.

---

# Using the chat

After running a check, you can ask follow-up questions in the chat box.

Examples:

* `Summarize the issues`
* `Which checks failed?`
* `Show TTM issues`
* `Show consistency issues`
* `What should I fix first?`
* `Explain TTM`

The assistant answers based on the results of the current campaign analysis.

## Important

The assistant does **not** currently edit the campaign for you.

It only helps you inspect and understand the current exported file.

---

# TTM checks

The current TTM check assumes a specific level structure with forward progression and relapse / at-risk levels.

If the assistant reports a TTM problem, it usually means one of these:

* a level points to the wrong next level
* a fallback / relapse transition is incorrect
* the intended progression structure is broken

If you want more detail, ask the chat:

* `Explain TTM`
* `Show TTM issues`

---

# Excel report export

The app automatically generates an Excel report of issues after every successful analysis. If issues are found, a download button will appear in the sidebar.

This is useful if:

* you want to archive the results
* you want to share them with someone else
* you prefer reviewing issues in Excel

---

# Common problems

## The app does not start

Make sure:

* Python is installed
* the project dependencies are installed
* you started the correct script

## Upload does nothing

Make sure the file is:

* a GameBus campaign export
* an `.xlsx` file
* not currently open in another program

## Download from GameBus fails

Possible causes:

* wrong credentials
* expired session
* network/server problem
* the campaign abbreviation is incorrect

If this happens, export the campaign manually and use file upload instead.

## I do not understand an error

Try asking the assistant:

* `Summarize the issues`
* `Explain TTM`
* `What should I fix first?`

If needed, also use the Excel report for the detailed raw output.

---

# Current limitations

This version of the app does **not** yet:

* edit campaigns directly in GameBus
* upload corrected files back into GameBus
* compare two campaign files
* generate campaign content
* fully validate all design or theory aspects automatically

It is mainly a user-friendly interface around the current checker.

---

# Need more help?

If available in your project, also check:

* `README.md`
* `docs/installation-windows.md`
* `docs/legacy-checker.md`
* `docs/ttm-checks.md`
