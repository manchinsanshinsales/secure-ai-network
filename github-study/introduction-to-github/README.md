# Introduction to GitHub（GitHub 入門）

> GitHub Skills 公式コース: https://github.com/skills/introduction-to-github

## コース概要

GitHub を使い始めるための基礎コース。1時間以内で完了できます。

- **対象**: 初めて GitHub を使う開発者・学生
- **前提知識**: なし
- **所要時間**: 1時間未満

---

## 学習内容

このコースで習得できる4つのスキル：

1. **ブランチの作成**（Create a branch）
2. **ファイルのコミット**（Commit a file）
3. **プルリクエストのオープン**（Open a pull request）
4. **プルリクエストのマージ**（Merge your pull request）

---

## 重要概念ノート

### リポジトリ（Repository）

- プロジェクトのファイルとその変更履歴をすべて保管する場所
- 略して「リポ」「repo」とも呼ぶ
- GitHub 上で公開（public）または非公開（private）に設定できる

### ブランチ（Branch）

- リポジトリの「作業用コピー」
- `main` ブランチが本番環境に相当するメインのブランチ
- 新機能や修正は別ブランチで作業し、完成したら `main` にマージする
- 複数人が同時に別々のブランチで作業できる

```
main ──────────────────────────────→
        ↘ feature/my-change → マージ ↗
```

### コミット（Commit）

- ファイルへの変更を記録するスナップショット
- コミットメッセージに「何を変更したか」を簡潔に書く
- コミットの積み重ねが変更履歴（History）になる

**コミットメッセージの書き方の例：**

```
Add profile README
Fix typo in welcome message
Update dependencies to latest version
```

### プルリクエスト（Pull Request / PR）

- 自分のブランチの変更を `main` ブランチに取り込んでほしいというリクエスト
- チームメンバーがコードをレビューしてフィードバックできる
- 議論・承認・マージの流れが1か所で管理できる

### マージ（Merge）

- ブランチの変更を別のブランチ（通常は `main`）に統合すること
- プルリクエストがレビュー済みで承認されたらマージする

---

## 基本的な作業フロー

```
1. リポジトリを作成（または Fork）
      ↓
2. ブランチを作成
      ↓
3. ファイルを編集・追加
      ↓
4. 変更をコミット
      ↓
5. プルリクエストを作成
      ↓
6. レビュー・議論
      ↓
7. マージして完了
```

---

## よく使うコマンド（参考）

```bash
# リポジトリをクローン
git clone https://github.com/ユーザー名/リポジトリ名.git

# ブランチを作成して切り替え
git checkout -b feature/my-feature

# 変更をステージング
git add .

# コミット
git commit -m "Add new feature"

# リモートにプッシュ
git push origin feature/my-feature
```

---

## 演習チェックリスト

- [ ] GitHub アカウントを作成した
- [ ] リポジトリを作成できた
- [ ] ブランチを作成できた
- [ ] ファイルを追加してコミットできた
- [ ] プルリクエストを作成できた
- [ ] プルリクエストをマージできた

---

## 参考リンク

- [GitHub Skills: Introduction to GitHub](https://github.com/skills/introduction-to-github)
- [GitHub ドキュメント - リポジトリ](https://docs.github.com/ja/repositories)
- [GitHub ドキュメント - ブランチ](https://docs.github.com/ja/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches)
- [GitHub ドキュメント - プルリクエスト](https://docs.github.com/ja/pull-requests)
