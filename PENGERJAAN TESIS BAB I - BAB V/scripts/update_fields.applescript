tell application "Microsoft Word"
	activate
	set docPath to POSIX file "/Volumes/WORK/MTI UNSIBANK/TESIS/PENGERJAAN TESIS BAB I - BAB V/Tesis_ITSNU_v10_Final.docx" as text
	open file docPath
	delay 2
	try
		update fields of active document
	end try
	try
		update table of contents 1 of active document
	end try
	save active document
end tell
