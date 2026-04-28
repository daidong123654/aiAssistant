on run
    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        set rows to {}
        repeat with elementRef in entire contents of p
            set textBlob to ""
            try
                set textBlob to textBlob & (role of elementRef as text)
            end try
            try
                set textBlob to textBlob & " | " & (name of elementRef as text)
            end try
            try
                set textBlob to textBlob & " | " & (description of elementRef as text)
            end try
            try
                set textBlob to textBlob & " | " & (title of elementRef as text)
            end try
            try
                set textBlob to textBlob & " | " & (value of elementRef as text)
            end try

            if textBlob is not "" then set end of rows to textBlob
        end repeat
    end tell

    set oldDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set outputText to rows as text
    set AppleScript's text item delimiters to oldDelimiters
    return outputText
end run

on firstWpsProcess()
    tell application "System Events"
        repeat with p in processes
            set processName to name of p
            if processName contains "WPS" or processName contains "wps" then return p
        end repeat
    end tell
    return missing value
end firstWpsProcess

