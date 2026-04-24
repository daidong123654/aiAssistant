#!/bin/bash

# 目标目录
CONSUME_DIR="/Users/jianfeisu/Work/tools/paperless-ngx/consume"

# 创建目录（如果不存在）
mkdir -p "$CONSUME_DIR"

# 定义一些随机内容词库
WORDS=(
    "Lorem" "ipsum" "dolor" "sit" "amet" "consectetur" "adipiscing" "elit"
    "sed" "do" "eiusmod" "tempor" "incididunt" "ut" "labore" "et" "dolore"
    "magna" "aliqua" "Ut" "enim" "ad" "minim" "veniam" "quis" "nostrud"
    "exercitation" "ullamco" "laboris" "nisi" "ut" "aliquip" "ex" "ea"
    "commodo" "consequat" "Duis" "aute" "irure" "dolor" "in" "reprehenderit"
    "voluptate" "velit" "esse" "cillum" "dolore" "eu" "fugiat" "nulla"
    "pariatur" "Excepteur" "sint" "occaecat" "cupidatat" "non" "proident"
)

# 中文词库
CHINESE_WORDS=(
    "春天" "夏天" "秋天" "冬天" "快乐" "悲伤" "兴奋" "平静" "工作" "学习"
    "思考" "创新" "梦想" "希望" "挑战" "机遇" "成长" "进步" "科技" "未来"
    "人工智能" "机器学习" "深度学习" "神经网络" "数据分析" "云计算" "物联网"
)

# 生成随机内容的函数
generate_content() {
    local word_count=1000
    local content=""
    
    for ((i=1; i<=word_count; i++)); do
        # 随机选择中英文
        if [ $((RANDOM % 2)) -eq 0 ]; then
            # 英文词
            content+="${WORDS[$((RANDOM % ${#WORDS[@]}))]} "
        else
            # 中文词
            content+="${CHINESE_WORDS[$((RANDOM % ${#CHINESE_WORDS[@]}))]} "
        fi
        
        # 每20个词换行
        if [ $((i % 20)) -eq 0 ]; then
            content+="\n"
        fi
    done
    echo "$content"
}

start=${1:-1}
end=${2:-100}
echo "start:$start end:$end"

# 生成100个文件
for i in $(seq $start $end); do
    # 生成文件名（补零到3位）
    filename=$(printf "document_%d.txt" $i)
    filepath="$CONSUME_DIR/$filename"
    
    # 生成随机内容
    echo "生成文件: $filename"
    generate_content > "$filepath"
    
    # 添加一些元数据信息
    echo -e "\n---\n文件编号: $i\n生成时间: $(date '+%Y-%m-%d %H:%M:%S')\n随机种子: $RANDOM" >> "$filepath"
done

echo "✅ 完成！共生成100个文件在 $CONSUME_DIR"
echo "文件列表："
ls -la "$CONSUME_DIR" | grep "document_"
