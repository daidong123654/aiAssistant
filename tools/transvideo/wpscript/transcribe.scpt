-- 1️⃣ 获取选中的音频文件
tell application "Finder"
	set selectedItems to selection
	if (count of selectedItems) is 0 then
		display dialog "请先在 Finder 中选中一个音频文件" buttons {"确定"} default button 1 with icon caution
		return
	end if
	set audioPath to POSIX path of (item 1 of selectedItems as alias)
end tell

-- 2️⃣ 设置项目路径 (请根据实际路径修改)
set projectPath to "/Users/Theast/Desktop/Work/ldf/农业/videos/whisper-go-pipeline"
set hfToken to "YOUR_HF_TOKEN" -- 填入你的 HuggingFace Token

-- 3️⃣ 运行转写
display notification "正在开始本地 ASR 转写..." with title "Whisper 自动化"

-- 注意：这里使用全路径，确保在自动化环境中能运行
set goPath to "/Users/Theast/.goenv/shims/go"
set shellCmd to "cd " & quoted form of projectPath & " && " & goPath & " run main.go " & quoted form of audioPath & " " & hfToken & " > output.txt 2>&1"

try
	do shell script shellCmd
	display notification "转写完成！结果已保存至 output.txt" with title "Whisper 自动化"
	
	-- 打开结果文件
	do shell script "open " & quoted form of (projectPath & "/output.txt")
on error errMsg
	display dialog "运行出错: " & errMsg buttons {"确定"} default button 1 with icon stop
end try
