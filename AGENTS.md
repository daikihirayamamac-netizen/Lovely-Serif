# AGENTS.md — Lovely Serif 引き継ぎ

Codex（や他のエージェント）が最初に読むファイル。ここだけ読めば作業を再開できるように書いてある。

## 1. これは何か

**Lovely Serif（ラブリーセリフ）** は、日本語と英語のための「やわらかな明朝体」。実際にインストール・配布・Web利用できる本物のフォントを作るプロジェクト（画像やCSS加工ではない）。

- ラテン = Nanum Myeongjo（NAVER/NHN, OFL 1.1）をベース
- 日本語 = Noto Serif JP（Adobe/Google, OFL 1.1）をベース
- 元データのアウトラインを編集して、固有のデザインにしている（角の丸め、筆の抜きのような終端、ウロコの丸み、日英の黒さ統一、代表文字の手作業編集）
- 現在: **v0.1.1 Regular のみ**。10,374グリフ。常用漢字2,136字、JIS X 0208/0213第1面の漢字を全収録
- ライセンス: SIL OFL 1.1。元フォントの著作権表示を保持。`Nanum` `Noto` `Source` は予約名なので派生版の名称に使わない

## 2. オーナーの意向（最優先で守る）

- オーナーは日本語話者。**やりとりは日本語**で、簡潔・率直・フレンドリー。実用性重視。
- 見た目の方向性は添付リファレンス画像どおり。英語は上品なまま、日本語に個性を持たせる。過剰な装飾は禁止。丸ゴシックにしない。
- ゑ・ヱ・ヹ・㋽ は**意図的に削除済み**（「気持ち悪い」ため）。復活させない。`lovelyserif/config.py` の `EXCLUDE_CODEPOINTS`。
- 「単なる結合・CSS加工・フォント名変更」は不可。実際のアウトライン編集であること。
- **未完成のものを完成と報告しない。** 検証できていないことは正直に書く。
- オーナーは個人サイトを持っていて、そのフォントを全部 Lovely Serif にしたい。**サイトのURL／プラットフォームは未確認**。次にオーナーへ聞くこと。woff2 と `fonts/lovely-serif.css` を置いて `font-family: "Lovely Serif", "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif` を指定するのが基本の導入方法。
- プレビューサイトのデザインはオーナーに好評（「こういうデザインが大好き」）。大きく変えない。

## 3. リポジトリ構成

| パス | 内容 |
|---|---|
| `lovelyserif/build.py` | ビルド本体。Noto をサブセット → Nanum ラテンに置換 → 全角英数合成 → アクセント合成 → デザインパス → OTF/TTF/WOFF2/UFO 生成 |
| `lovelyserif/filters.py` | 角丸め `soften_corners`、接線平滑化 `smooth_joins`、重なり除去、輪郭オフセット `offset_outline` |
| `lovelyserif/edits.py` | 手作業編集（永 美 文 字 あ の り は か す、m n i l k の払い など）。`@register("グリフ名")` で追加 |
| `lovelyserif/config.py` | **デザインパラメータ**（半径・太さ補正・除外文字・メトリクス・名前・バージョン） |
| `lovelyserif/qa.py` | 輪郭QA（元フォントとのラスタ比較、自己交差、縮退、向き、消失） |
| `lovelyserif/outline.py` `geometry.py` | 輪郭モデル（3次ベジェ、PS向き=外側反時計回り）と幾何ヘルパー |
| `lovelyserif/coverage.py` `report.py` `render.py` | 収録範囲、レポート、SVG描画 |
| `scripts/build.py` | フルビルド（`--fetch` で元フォント取得、`--quick` でTTFのみ） |
| `scripts/lab.py` | 少数の文字でパラメータ試作（数秒）。`--set KANJI_PARAMS.r_convex=24` |
| `scripts/qa.py` `verify.py` | QAと総合検証 → `reports/qa.md` `reports/verification.md` |
| `scripts/make_webfonts.py` `make_preview.py` | 軽量woff2＋CSS、プレビューサイト生成 |
| `scripts/dev/*.js` | Playwright 製のスクショ／スマホ幅チェック（`mobile_check.js`） |
| `fonts/` | 成果物（OTF, TTF, WOFF2, -std.woff2, CSS） |
| `sources/LovelySerif-Regular.ufo.zip` | 編集済みUFOマスター（解凍して使う。展開版は gitignore） |
| `sources/upstream/` | 元フォント（gitignore。`--fetch` で取得、SHA-256検証） |
| `preview/` | `template.html` が元、`index.html` は生成物 |
| `reports/` | グリフ状態一覧、収録範囲、検証結果、Before/After SVG、QA |
| `data/joyo.txt` | 常用漢字2,136字（公式2010年版の字体） |
| `tests/test_fonts.py` | 成果物のスモークテスト |

## 4. よく使うコマンド

```bash
pip install -r requirements.txt            # FontForge は不要（fontTools + skia-pathops）
python scripts/build.py --fetch            # フルビルド（約2分半）。fonts/ reports/ sources/*.ufo を更新
python scripts/make_webfonts.py            # fonts/LovelySerif-Regular-std.woff2 と CSS
python scripts/make_preview.py             # preview/index.html
(cd sources && rm -f LovelySerif-Regular.ufo.zip && zip -q -r LovelySerif-Regular.ufo.zip LovelySerif-Regular.ufo)
python scripts/qa.py                       # 輪郭QA（約2分）。構造的な破綻は 0 件であること
python scripts/verify.py                   # 総合検証（fontTools/OTS/HarfBuzz/FreeType/字間/FontBakery）
python -m unittest discover -s tests -v    # スモークテスト
node scripts/dev/mobile_check.js           # プレビューのスマホ幅チェック（要 playwright）
python scripts/lab.py --out /tmp/lab/A.ttf --set KANJI_PARAMS.r_convex=24   # デザイン試作
```

見た目の調整は `lovelyserif/config.py` のパラメータを変えて再ビルドするのが基本。コミット前に `qa.py` と `verify.py` を必ず通す。

## 5. 現在の状態（正直に）

**検証済み（`reports/verification.md` `reports/qa.md`）**
- 輪郭の破綻（自己交差・縮退・向き違い・消失）0件 / 10,374グリフ
- OTS クリーン（OTF/TTF/WOFF2）、FontBakery universal FAIL 0（WARN 10: ファイルサイズ、post format 3、chws/vchw 無し等）
- HarfBuzz で vert/vrt2/palt/kern/fwid 動作確認、Latin 2,500ペアで新規の衝突 0
- 常用漢字2,136字: フル版・軽量版とも全収録
- Chromium で横書き・縦書き・混植を目視確認、プレビューはスマホ幅でも崩れなし

**未検証・未完了（完成扱いにしない）**
- **実機の macOS Font Book でのインストール確認はまだ**（名前・メタデータの検証だけ）
- デザインの良し悪しはレンダリング画像での確認のみ。オーナーの最終判断はこれから
- ウェイトは Regular のみ
- ヒンティング無し（Windows の小サイズは粗い可能性）
- 中欧系ラテン（Č Š Ž Ğ Ő など Latin Extended-A の大半）は未収録（Noto に無い。Nanum 基本字＋アクセント合成で増やせる）
- ラテンのカーニングは Nanum の55ペアのみ
- IVS（異体字セレクタ）未収録、chws/vchw 未実装
- 手作業編集は代表文字のみ。その他は自動処理（角丸め・平滑化・太さ補正）

## 6. 次にやること（優先順）

1. オーナーにプレビューの感想を聞く（もっと丸く／シャープに／英語を細く など）→ `config.py` を調整して再ビルド
2. オーナーのサイトにフォントを導入（URL／プラットフォームを聞く。woff2 配置と CSS 差し替え。必要なら軽量版 `-std.woff2` を使う）
3. ウェイト展開 Light / Medium / SemiBold / Bold。素材: `sources/upstream/NotoSerifJP-Medium.otf`、Noto 可変フォント `https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/Variable/OTF/Subset/NotoSerifJP-VF.otf`（`fvar` wght 200–900、12MB。`sources.py` には未登録なので使うなら追加してSHA-256を固定する）、`NanumMyeongjo-Bold.ttf`。**単純な太さ変更だけで完成扱いにしない**（日英の黒さを揃え、手作業編集を各ウェイトに適用）
4. 実機 macOS Font Book での確認、必要ならヒンティング（ttfautohint 等）
5. 手作業編集の拡大（「愛」「国」「あ行」以外のかな、カタカナ、よく使う漢字）
6. 中欧系ラテンの追加、カーニング拡充

## 7. ハマりどころ（過去に踏んだバグ）

- **skia-pathops のブール演算を面積比較に使わない。** XOR面積は入れ子輪郭を二重カウントし、`simplify(fix_winding=True)` はCJKの重なり輪郭で結果が不安定。`qa.py` は自前の非ゼロ巻き数ラスタライザで比較している。
- 角丸めは輪郭の自己交差を起こすことがある。`design_pass` が検出して半径を 0.6 → 0.35 → 0 倍で自動リトライする。新しい加工を足したら必ず `qa.py` を回す。
- Latin の +3 太さ補正は字間を詰める。`_shape` で幅を `+2*LATIN_OFFSET` 広げて補正済み。補正値を変えたら `verify.py` の字間チェックを見る。
- TTF は post format 3（グリフ名なし）。OTF とグリフ順は同じだがグリフ名で引けない。比較は順序でマップする（`verify.py` 参照）。
- Noto のアクセント付きLatinは Nanum と太さが違うため使わない。`compose_accented` が Noto の合成字からアクセント部品だけ抜いて Nanum の基本字に載せる。Ç ç はベースと一体輪郭なので差分演算で切り出している。
- UFO展開版は約150MBでgitignore。コミットするのはzipだけ。ビルドのたびにzipを作り直す。
- クラウドサンドボックスのネットワークは制限あり。`raw.githubusercontent.com` と PyPI は通るが、fonts.google.com、deb.debian.org などは不可。FontBakery の namecheck はオフラインで失敗するので `-x fontdata_namecheck` で除外している。

## 8. Git / PR

- 作業ブランチ: `claude/adoring-dijkstra-860yix`。ドラフトPR [#1](https://github.com/daikihirayamamac-netizen/Lovely-Serif/pull/1)（base: `main`）。マージはオーナーの判断待ち。
- 続きを作業するなら、このブランチに積むか、マージ後に `main` から新ブランチを切る。
- 大きなバイナリ（fonts/、UFO zip）はコミットして構わないが、1ファイル100MBは超えさせない（現状最大 21MB）。
- 変更したらレポート類（`reports/`）も再生成してコミットに含める。
