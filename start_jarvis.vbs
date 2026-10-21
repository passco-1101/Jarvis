' Starts the Jarvis daemon in the background with no window. The Startup-folder shortcut runs this file.
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
shell.Run "pythonw.exe -m jarvis serve", 0, False
