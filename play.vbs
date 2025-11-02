Dim fso, shell, scriptDir, pythonExe, target, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = fso.BuildPath(scriptDir, ".venv\Scripts\python.exe")
target = fso.BuildPath(scriptDir, "run.py")

If Not fso.FileExists(pythonExe) Then
	' Fallback to system Python if venv not found
	pythonExe = "python"
End If

cmd = """" & pythonExe & """ """ & target & """"
shell.Run cmd, 0, False
