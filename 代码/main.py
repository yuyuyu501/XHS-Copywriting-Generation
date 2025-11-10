from 主干.生成文案 import process_texts
from 支线.教育.json转word import json_to_word

if __name__ == '__main__':
    input_file= "D://小红书文案2//文案//教育//原始文案//original_school_texts.json"
    output_file = "D://小红书文案2//文案//教育//生成文案//finally_school_texts.json"
    process_texts(input_file, output_file)

    json_to_word(output_file)