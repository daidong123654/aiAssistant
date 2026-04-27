-- 1️⃣ 获取 Finder 当前选中文件
tell application "Finder"
	activate
	set selectedItems to selection
	if (count of selectedItems) is 0 then
		display dialog "请先在 Finder 中选中一个音频文件" buttons {"确定"} default button 1 with icon caution
		return
	end if
	set theFile to item 1 of selectedItems
	select theFile
end tell

delay 1

tell application "System Events"
	tell process "Finder"
		set frontmost to true
		
		-- 触发你设置的快捷键 (Ctrl + Opt + T)
		-- 注意：请确保已在 Finder 中为“WPS 听记”或相关服务设置此快捷键
		keystroke "t" using {control down, option down}
	end tell
end tell

delay 5

-- 3️⃣ 操作 WPS 转写窗口
tell application "System Events"
	-- 寻找 WPS 进程，排除后台进程
	set wpsProc to first process whose background only is false and (name contains "wps" or name contains "WPS")
	
	tell wpsProc
		set frontmost to true
		delay 2
		
		-- 寻找窗口 1（转写设置窗口）
		tell window 1
			-- 勾选“区分说话人”
			try
				if exists (first checkbox whose name contains "区分说话人") then
					click (first checkbox whose name contains "区分说话人")
					delay 1
				end if
			end try
			
			-- 选择“多人讨论”
			try
				if exists (first radio button whose name contains "多人") then
					click (first radio button whose name contains "多人")
					delay 1
				end if
			end try
			
			-- 点击“开始转写”
			try
				click (first button whose name contains "开始")
			on error
				display dialog "未找到'开始转写'按钮，请检查 WPS 窗口状态"
			end try
		end tell
	end tell
end tell

-- 4️⃣ 等待转换完成（轮询）
delay 10

tell application "System Events"
	set wpsProc to first process whose background only is false and (name contains "wps" or name contains "WPS")
	
	tell wpsProc
		repeat 60 times -- 最多等待 5 分钟 (60 * 5s)
			delay 5
			try
				if exists (first button whose name contains "导出") then
					exit repeat
				end if
			end try
		end repeat
		
		tell window 1
			-- 点击“更多”或“...”
			try
				click (first button whose name contains "更多" or name contains "...")
				delay 1
			end try
			
			-- 点击“导出”
			try
				click (first menu item whose name contains "导出")
			on error
				-- 如果“导出”不在菜单里，可能直接在窗口上
				click (first button whose name contains "导出")
			end try
		end tell
	end tell
end tell

delay 2

-- 5️⃣ 勾选导出选项
tell application "System Events"
	set wpsProc to first process whose background only is false and (name contains "wps" or name contains "WPS")
	
	tell wpsProc
		tell window 1
			-- 勾选“原文”
			try
				click (first checkbox whose name contains "原文")
			end try
			
			-- 勾选“附加信息”
			try
				click (first checkbox whose name contains "附加")
			end try
			
			delay 1
			
			-- 点击最终的“导出”按钮
			try
				click (first button whose name contains "导出")
			end try
		end tell
	end tell
end tell
