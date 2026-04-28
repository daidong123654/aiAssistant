on run argv
    if (count of argv) is less than 1 then error "usage: export.scpt filePath [startDelay] [conversionTimeout]"

    set filePath to item 1 of argv
    set startDelay to 5
    set conversionTimeout to 1800

    if (count of argv) is greater than 1 then set startDelay to (item 2 of argv as number)
    if (count of argv) is greater than 2 then set conversionTimeout to (item 3 of argv as number)

    tell application "System Events"
        if not (exists disk item filePath) then error "File not found: " & filePath
    end tell

    delay startDelay

    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        tell p
            set frontmost to true
        end tell

        my clickText(p, {"上传音视频"})
        delay 1
        my clickText(p, {"立即上传"})
        delay 1
    end tell

    my chooseFile(filePath)
    delay 2

    my waitUntilReadyToDownload(conversionTimeout)
    my openTaskMoreMenu()
    delay 1
    my clickDownloadSourceText()
    delay 2
    my confirmDownloadDialogs()
end run

on chooseFile(filePath)
    tell application "System Events"
        keystroke "g" using {command down, shift down}
        delay 0.5
        keystroke filePath
        delay 0.3
        key code 36
        delay 0.8
        key code 36
    end tell
end chooseFile

on waitUntilReadyToDownload(timeoutSeconds)
    set pollDelay to 5
    set maxLoops to timeoutSeconds div pollDelay
    if maxLoops is less than 1 then set maxLoops to 1

    repeat with loopIndex from 1 to maxLoops
        tell application "System Events"
            set p to my firstWpsProcess()
            if p is missing value then error "WPS process not found"

            if my existsText(p, {"下载源文", "已完成", "转换完成", "转写完成"}) then
                return true
            end if
            if my existsText(p, {"失败", "上传失败", "转换失败", "转写失败"}) then
                error "WPS task failed"
            end if
        end tell

        delay pollDelay
    end repeat

    error "Timed out waiting for WPS conversion"
end waitUntilReadyToDownload

on openTaskMoreMenu()
    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        set candidates to my matchingElements(p, {"更多", "..."})
        if (count of candidates) is 0 then error "More menu button not found"

        click item -1 of candidates
    end tell
end openTaskMoreMenu

on clickDownloadSourceText()
    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        my clickText(p, {"下载源文", "源文"})
    end tell
end clickDownloadSourceText

on confirmDownloadDialogs()
    tell application "System Events"
        delay 1
        key code 36
        delay 1
        key code 36
    end tell
end confirmDownloadDialogs

on clickText(rootElement, tokens)
    set candidates to my matchingElements(rootElement, tokens)
    if (count of candidates) is 0 then
        error "UI element not found: " & (item 1 of tokens)
    end if
    tell application "System Events"
        click item 1 of candidates
    end tell
end clickText

on existsText(rootElement, tokens)
    set candidates to my matchingElements(rootElement, tokens)
    return ((count of candidates) is greater than 0)
end existsText

on matchingElements(rootElement, tokens)
    set matches to {}

    tell application "System Events"
        try
            set allElements to entire contents of rootElement
        on error
            set allElements to {}
        end try

        repeat with elementRef in allElements
            set textBlob to ""
            try
                set textBlob to textBlob & " " & (name of elementRef as text)
            end try
            try
                set textBlob to textBlob & " " & (description of elementRef as text)
            end try
            try
                set textBlob to textBlob & " " & (title of elementRef as text)
            end try
            try
                set textBlob to textBlob & " " & (value of elementRef as text)
            end try

            repeat with tokenRef in tokens
                set tokenText to tokenRef as text
                if textBlob contains tokenText then
                    set end of matches to elementRef
                    exit repeat
                end if
            end repeat
        end repeat
    end tell

    return matches
end matchingElements

on firstWpsProcess()
    tell application "System Events"
        repeat with p in processes
            set processName to name of p
            if processName contains "WPS" or processName contains "wps" then return p
        end repeat
    end tell
    return missing value
end firstWpsProcess
