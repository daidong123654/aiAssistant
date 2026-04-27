on run argv
    set filePath to item 1 of argv
    set quickActionKey to "t"
    if (count of argv) is greater than 1 then set quickActionKey to item 2 of argv

    tell application "System Events"
        if not (exists disk item filePath) then error "File not found: " & filePath
    end tell

    set targetFile to POSIX file filePath as alias

    tell application "Finder"
        activate
        open container of targetFile
        delay 0.5
        set selection to targetFile
    end tell

    delay 1

    tell application "System Events"
        tell process "Finder"
            set frontmost to true
            keystroke quickActionKey using {control down, option down}
        end tell
    end tell
end run
