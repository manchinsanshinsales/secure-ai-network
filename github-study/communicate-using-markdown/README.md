# Communicate using Markdown（Markdown でのコミュニケーション）

> GitHub Skills 公式コース: https://github.com/skills/communicate-using-markdown

## コース概要

Markdown を使って、Issue やプルリクエストのコメントをわかりやすく整形するコース。

- **対象**: 初めて GitHub を使う開発者・学生
- **前提知識**: [Introduction to GitHub](../introduction-to-github/) を完了していることを推奨
- **所要時間**: 1時間未満

---

## 学習内容

このコースで習得できる5つのスキル：

1. **見出しの追加**（Add headers）
2. **画像の追加**（Add an image）
3. **コード例の追加**（Add a code example）
4. **タスクリストの作成**（Make a task list）
5. **プルリクエストのマージ**（Merge your pull request）

---

## Markdown 基本構文チートシート

### 見出し（Headers）

```markdown
# 見出し1（最大）
## 見出し2
### 見出し3
#### 見出し4
```

**表示例：**

# 見出し1
## 見出し2
### 見出し3

---

### テキストの装飾

```markdown
**太字**
*イタリック*
~~打ち消し~~
`インラインコード`
```

| 記法 | 表示 |
|------|------|
| `**太字**` | **太字** |
| `*イタリック*` | *イタリック* |
| `~~打ち消し~~` | ~~打ち消し~~ |
| `` `コード` `` | `コード` |

---

### リスト

**箇条書きリスト：**
```markdown
- 項目1
- 項目2
  - サブ項目2-1
  - サブ項目2-2
- 項目3
```

**番号付きリスト：**
```markdown
1. 最初のステップ
2. 次のステップ
3. 最後のステップ
```

---

### タスクリスト（チェックボックス）

GitHub の Issue やプルリクエストで使える特殊なリスト。

```markdown
- [x] 完了したタスク
- [ ] まだのタスク
- [ ] 別のタスク
```

表示例：
- [x] 完了したタスク
- [ ] まだのタスク
- [ ] 別のタスク

---

### コードブロック

**インラインコード（1行）：**
```markdown
`git commit -m "message"`
```

**コードブロック（複数行）：**
````markdown
```python
def hello():
    print("Hello, World!")
```
````

**言語を指定するとシンタックスハイライトが効く：**

```python
def hello():
    print("Hello, World!")
```

```bash
git checkout -b feature/my-branch
git add .
git commit -m "Add feature"
```

---

### リンクと画像

**リンク：**
```markdown
[表示テキスト](https://example.com)
```

**画像：**
```markdown
![代替テキスト](画像のURL)
```

**リポジトリ内の画像を参照する場合：**
```markdown
![図の説明](./images/diagram.png)
```

---

### 表（テーブル）

```markdown
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| D   | E   | F   |
```

表示例：

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| D   | E   | F   |

---

### 引用（Blockquote）

```markdown
> これは引用です。
> 複数行にまたがることもできます。
```

> これは引用です。
> 複数行にまたがることもできます。

---

### 水平線

```markdown
---
```

---

### 絵文字（Emoji）

GitHub では絵文字コードが使えます。

```markdown
:white_check_mark: 完了
:x: 未完了
:warning: 注意
:bulb: ヒント
:rocket: リリース
```

:white_check_mark: 完了 / :x: 未完了 / :warning: 注意 / :bulb: ヒント / :rocket: リリース

---

### 折りたたみ（Details / Summary）

長い内容を折りたたんで表示できます。

```markdown
<details>
<summary>クリックして展開</summary>

ここに隠したい内容を書きます。

</details>
```

---

## GitHub での Markdown 活用場面

| 場面 | 活用例 |
|------|--------|
| Issue | バグ報告にコードブロックや画像を添付 |
| プルリクエスト | 変更内容をリストや表で整理 |
| コメント | チェックリストで進捗を管理 |
| README.md | プロジェクトの説明を見出しや表で整形 |
| Wiki | ドキュメントを階層構造で整理 |

---

## 演習チェックリスト

- [ ] 見出し（`#`）を使ったファイルを作成できた
- [ ] 画像を Markdown に埋め込めた
- [ ] コードブロックにシンタックスハイライトを設定できた
- [ ] タスクリスト（`- [ ]`）を作成できた
- [ ] 表（テーブル）を作成できた
- [ ] プルリクエストで Markdown を使ったコメントを書けた

---

## 参考リンク

- [GitHub Skills: Communicate using Markdown](https://github.com/skills/communicate-using-markdown)
- [GitHub Markdown の基本構文](https://docs.github.com/ja/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
- [GitHub Flavored Markdown 仕様](https://github.github.com/gfm/)
- [絵文字チートシート](https://github.com/ikatyang/emoji-cheat-sheet)
