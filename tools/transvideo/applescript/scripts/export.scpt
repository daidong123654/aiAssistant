on run argv
    set startDelay to 5
    set exportDelay to 60

    if (count of argv) is greater than 0 then set startDelay to (item 1 of argv as number)
    if (count of argv) is greater than 1 then set exportDelay to (item 2 of argv as number)

    delay startDelay

    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        tell p
            set frontmost to true
            try
                click (first button of window 1 whose name contains "开始")
            end try
        end tell
    end tell

    delay exportDelay

    tell application "System Events"
        set p to my firstWpsProcess()
        if p is missing value then error "WPS process not found"

        tell p
            set frontmost to true
            tell window 1
                try
                    click (first button whose name contains "更多")
                    delay 1
                    click (first menu item of p whose name contains "导出")
                on error
                    try
                        click (first button whose name contains "...")
                        delay 1
                        click (first menu item of p whose name contains "导出")
                    end try
                end try
            end tell
        end tell
    end tell
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

