# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : module.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 14:25
import json
import os


class JsonDict(dict):
    def __init__(self, filename='xx.json', data: dict=None, indent=4):
        """
        初始化 JsonDict 对象。

        :param filename: JSON 文件的路径，默认为 'xx.json'
        :param indent: 写入 JSON 文件时的缩进空格数，默认为 4
        """
        super().__init__()
        if data is None:
            data = {}
        self.filename = filename
        self.indent = indent
        self.load()
        self.data = data

    def load(self):
        """
        从 JSON 文件中加载数据到内存。
        如果文件不存在，则初始化为空字典。
        """
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                print(f"警告: {self.filename} 文件内容不是有效的 JSON 格式。初始化为空字典。")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        """
        将内存中的数据保存到 JSON 文件。
        """
        try:
            with open(self.filename, 'w+', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=self.indent)
        except Exception as e:
            print(f"保存 JSON 文件时出错: {e}")

    def __getitem__(self, key):
        """
        通过键获取值。如果键不存在，则抛出 KeyError。
        """
        return self.data[key]

    def __setitem__(self, key, value):
        """
        通过键设置值，并保存到 JSON 文件。
        """
        self.data[key] = value
        print(value)
        print(self.data)
        self.save()

    def __delitem__(self, key):
        """
        通过键删除对应的键值对，并保存到 JSON 文件。
        """
        if key in self.data:
            del self.data[key]
            self.save()
        else:
            raise KeyError(f"键 '{key}' 不存在。")

    def __contains__(self, key):
        """
        检查键是否存在。
        """
        return key in self.data

    def keys(self):
        """
        返回所有键的迭代器。
        """
        return self.data.keys()

    def values(self):
        """
        返回所有值的迭代器。
        """
        return self.data.values()

    def items(self):
        """
        返回所有键值对的迭代器。
        """
        return self.data.items()

    def get(self, key, default=None):
        """
        获取指定键的值，如果键不存在则返回默认值。
        """
        return self.data.get(key, default)

    def clear(self):
        """
        清空所有数据，并保存到 JSON 文件。
        """
        self.data.clear()
        self.save()

    def update(self, other):
        """
        使用另一个字典或可迭代的键值对更新当前字典，并保存到 JSON 文件。
        """
        self.data.update(other)
        self.save()

    def __repr__(self):
        """
        返回对象的字符串表示。
        """
        return f"JsonDict({self.data})"

    def __str__(self):
        """
        返回对象的字符串表示。
        """
        return str(self.data)