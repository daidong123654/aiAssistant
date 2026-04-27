-- 1️⃣ 设置变量
tell application "Finder"
    set selectedItems to selection
    if (count of selectedItems) is 0 then
        error "请先在 Finder 中选中一个音频文件。"
    end if
    set audioPath to POSIX path of (item 1 of selectedItems as alias)
end tell
set exportPath to audioPath & ".docx"

on firstVisibleWpsProcess()
    tell application "System Events"
        repeat with theProc in processes
            try
                set procName to name of theProc
                if (background only of theProc is false) and ((procName contains "WPS") or (procName contains "wps")) then return theProc
            end try
        end repeat
    end tell
    error "未能启动 WPS，请检查路径或手动启动。"
end firstVisibleWpsProcess

on firstButtonContaining(theWindow, keywords)
    tell application "System Events"
        try
            set elementName to name of theWindow as text
        on error
            set elementName to ""
        end try
        try
            set elementDescription to description of theWindow as text
        on error
            set elementDescription to ""
        end try
        
        repeat with keywordText in keywords
            if (elementName contains (keywordText as text)) or (elementDescription contains (keywordText as text)) then return theWindow
        end repeat
        
        repeat with childElement in UI elements of theWindow
            try
                return my firstButtonContaining(childElement, keywords)
            end try
        end repeat
    end tell
    error "未找到匹配按钮。"
end firstButtonContaining

on clickWindowRelative(theWindow, xRatio, yRatio)
    tell application "System Events"
        set windowPosition to position of theWindow
        set windowSize to size of theWindow
        set clickX to (item 1 of windowPosition) + ((item 1 of windowSize) * xRatio)
        set clickY to (item 2 of windowPosition) + ((item 2 of windowSize) * yRatio)
        click at {clickX as integer, clickY as integer}
    end tell
end clickWindowRelative

on clickByKeywordsOrRelative(theWindow, keywords, xRatio, yRatio)
    try
        set targetElement to my firstButtonContaining(theWindow, keywords)
        tell application "System Events" to click targetElement
    on error
        my clickWindowRelative(theWindow, xRatio, yRatio)
    end try
end clickByKeywordsOrRelative

on hasWpsListeningWindow(wpsProc)
    tell application "System Events"
        tell wpsProc
            repeat with theWindow in windows
                try
                    if (name of theWindow as text) contains "听记" then return true
                end try
            end repeat
        end tell
    end tell
    return false
end hasWpsListeningWindow

-- 2️⃣ 启动 WPS
tell application "/Applications/wpsoffice.app" to activate
delay 8

tell application "System Events"
    -- 找到 WPS 进程
    try
        set wpsProc to my firstVisibleWpsProcess()
    on error
        error "未能启动 WPS，请检查路径或手动启动。"
        return
    end try
    
    tell wpsProc
        set frontmost to true
        delay 2
        
        -- 3️⃣ 打开“音视频转文字”
        -- 用户指明：在主页右侧边栏的“热门服务”中
        set windowTitle to ""
        try
            set windowTitle to name of window 1 as text
        end try
        
        if windowTitle does not contain "听记" then
            try
                tell window 1
                    set entryPoint to my firstButtonContaining(it, {"音视频转文字"})
                    click entryPoint
                end tell
            on error
                -- 如果右侧“热门服务”中没找到，尝试点击菜单栏作为最后的备份
                try
                    click menu item "听记" of menu "工具" of menu bar 1
                on error
                    if not my hasWpsListeningWindow(wpsProc) then
                        error "未能找到主页右侧边栏【热门服务】中的【音视频转文字】。请确保 WPS 处于主页状态且该功能可见。"
                        return
                    end if
                end try
            end try
        end if
        
        delay 5
        
        -- 4️⃣ 点击“导入音频”
        try
            tell window 1
                my clickByKeywordsOrRelative(it, {"导入", "上传", "添加", "选择文件"}, 0.5, 0.55)
            end tell
        on error
            error "未能找到【导入】按钮"
            return
        end try
    end tell
    
    -- 5️⃣ 处理文件选择对话框
    delay 2
    keystroke "G" using {command down, shift down}
    delay 2
    keystroke audioPath
    delay 1
    keystroke return
    delay 2
    keystroke return -- 确定选择
    delay 3
    
    -- 6️⃣ 点击“开始转写”
    tell wpsProc
        try
            tell window 1
                -- 有些版本是“确认转写”或“开始”
                my clickByKeywordsOrRelative(it, {"开始", "确认", "转写"}, 0.78, 0.82)
            end tell
        on error
            error "未能找到【开始转写】按钮"
            return
        end try
    end tell
    
    -- 7️⃣ 等待处理完毕（轮询“导出”按钮）
    -- 视频转文字需要时间，每 10 秒检查一次，最多等 10 分钟
    set isFinished to false
    set maxWait to 60 
    set waitCount to 0
    
    repeat until isFinished or waitCount > maxWait
        tell wpsProc
            try
                -- 检查是否存在“导出”按钮
                set exportReadyButton to my firstButtonContaining(window 1, {"导出", "导出文档"})
                if exportReadyButton is not missing value then
                    set isFinished to true
                end if
            end try
        end tell
        if not isFinished then
            delay 10
            set waitCount to waitCount + 1
        end if
    end repeat
    
    if not isFinished then
        error "转写耗时过长，脚本停止等待。请在转写完成后手动导出。"
        return
    end if
    
    -- 8️⃣ 导出为 Word
    tell wpsProc
        tell window 1
            try
                my clickByKeywordsOrRelative(it, {"导出"}, 0.9, 0.12)
                delay 3
                
                -- 点击“导出为 Word”或“导出为文档”
                -- 通常会弹出一个菜单或对话框
                keystroke return -- 很多时候默认就是 Word，直接回车
                delay 2
            on error
                error "导出过程中无法点击按钮，请手动完成导出。"
                return
            end try
        end tell
    end tell
    
    -- 9️⃣ 处理保存对话框
    delay 2
    keystroke "G" using {command down, shift down}
    delay 2
    keystroke exportPath
    delay 1
    keystroke return
    delay 2
    keystroke return -- 确认保存文件名
    delay 1
    -- 如果提示文件已存在，可能需要额外处理，这里假设是覆盖或新文件
    keystroke return 
    
end tell
