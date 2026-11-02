# Lovely Serif（ラブリーセリフ）

**文字から、美しさを。** — 日本語と英語のための、やわらかな明朝体。

Lovely Serif は、実際にインストール・配布・Web 利用できる独自フォントです。
ラテン文字は **Nanum Myeongjo**、日本語は **Noto Serif JP** を元に、アウトラインそのものを編集して作っています
（角の丸め・筆の抜きのような終端・ウロコの丸み・日英の黒さの統一・代表文字の手作業編集）。
単なるフォント結合や名前の変更ではありません。

| ファイル | 用途 |
|---|---|
| `fonts/LovelySerif-Regular.otf` | macOS / Windows / Adobe アプリ向け（CFF アウトライン、グリフ名あり） |
| `fonts/LovelySerif-Regular.ttf` | TrueType 版（Web / Font Book どちらでも可） |
| `fonts/LovelySerif-Regular.woff2` | Web フォント（全収録文字、約 2.1 MB） |
| `fonts/LovelySerif-Regular-std.woff2` | Web 用軽量サブセット（ラテン・かな・記号・JIS 第1水準＋常用漢字、約 1 MB） |
| `fonts/lovely-serif.css` | そのまま使える `@font-face` |
| `preview/index.html` | タイプテスター付きプレビューサイト（自由に入力して確認できます） |
| `sources/LovelySerif-Regular.ufo.zip` | 編集済みマスター（UFO 形式、Glyphs / RoboFont / FontForge で開けます） |
| `reports/` | 検証結果・グリフ状態一覧・Before/After 比較 |

## プレビュー

`preview/index.html` をブラウザで開くと、実際の Lovely Serif（woff2）で自由に文字を入力して確認できます
（縦書き・palt・Noto Serif JP との比較トグル付き）。GitHub Pages を有効にすると `/preview/` で公開できます。

## 自分のサイトで使う

```css
@font-face {
  font-family: "Lovely Serif";
  src: url("/fonts/LovelySerif-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
html, body { font-family: "Lovely Serif", "Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif; }
.tate { writing-mode: vertical-rl; }              /* 縦書き */
.palt { font-feature-settings: "palt" 1; }        /* 詰め組み */
```

`fonts/LovelySerif-Regular.woff2`（と必要なら `-std.woff2`）をサイトに置くだけです。
macOS では `LovelySerif-Regular.otf` をダブルクリック → Font Book で「インストール」。
Font Book には「Lovely Serif」（日本語環境では「ラブリーセリフ」）として表示されます。

## デザイン

* **ベース**：ラテン = Nanum Myeongjo Regular（1024 → 1000 upm に縮小、重なり除去）／日本語 = Noto Serif JP Regular。
  計測の結果、Nanum の縦画 60–65 unit に対し漢字の縦画は 67–68 unit。ラテンは全体を +3 unit 太らせて黒さを揃えました
  （Noto 自身のラテンは 82–89 unit で重すぎるため不採用）。
* **角の丸め**（`lovelyserif/filters.py: soften_corners`）：すべての鋭角コーナーに小さなフィレットを入れます。
  凸（画の終端・ウロコ）は半径 30、凹（画の交差）は半径 10、鋭い先端（ハライ）は 18 unit のトリムで「丸ゴシック」にならない範囲で柔らかく。
  かなは 28 / 9 / 18、ラテンは 14 / 7 / 9（ウェイトに応じて自動的に縮小）。
* **接線の平滑化**（`smooth_joins`）：かなの筆の入り・抜きにある小さな折れ（22° 以下）を G1 連続にし、曲線をなめらかに。
* **手作業編集**（`lovelyserif/edits.py`）：永・美・文（ハライの伸長とテーパー、点の形、ウロコの丸み）、字、
  あ・の・り・は・か・す（終筆を筆の抜きのように伸ばす）、m・n・i・l・k（右足のセリフに繊細な上向きの払い）。
* **全角英数**（Ａ–ｚ）：Nanum のラテンを全角ボディに中央配置して合成（Noto の全角英数は不採用）。
* **メトリクス**：縦方向のメトリクスは Noto Serif JP と同一（typo 880/−120、hhea 1151/−286）。
  Noto Serif JP を使っているページをそのまま置き換えても行送りが変わりません。縦書き（vert/vrt2/vpal/vkrn/vhal）、
  palt/halt、fwid/hwid/pwid、locl/ccmp/liga を保持。ラテンのカーニングは Nanum の 55 ペアを移植。

Before/After は `reports/compare.html`（SVG、節点表示付き）とプレビューサイトの「Before / After」で確認できます。

## 収録文字（v0.1）

| セット | 収録 |
|---|---|
| ASCII / Latin-1 | 全て（アクセント付きは Nanum の基本字から合成） |
| Latin Extended-A | Ā ā Ē ē Ī ī Ō ō Ū ū Œ œ Ł ł ŋ ħ など一部 |
| ひらがな・カタカナ・半角カナ・全角英数記号 | 全て（ただし ゑ・ヱ・ヹ・㋽ は意図的に除外） |
| JIS X 0208 漢字（第1・第2水準） | 6,356 / 6,356 |
| JIS X 0213 第1面の漢字（常用漢字 2,136 字と人名用漢字をすべて含む） | 7,615 / 7,615 |
| 記号（①②③、㈱、℃、矢印、罫線、○●◎□■☆★ など） | Noto Serif JP の収録分 |

合計 10,374 グリフ・10,130 文字。常用漢字 2,136 字の全収録は `data/joyo.txt` と照合して検証しています。詳細は `reports/coverage.md`、全グリフの状態（元フォント／適用した加工／手作業編集）は `reports/glyph_status.csv` と `reports/glyph_status.md`。

## ビルド方法（再現可能）

```bash
pip install -r requirements.txt
python scripts/build.py --fetch       # 元フォントを取得（SHA-256 検証）→ fonts/ sources/*.ufo reports/ を生成
python scripts/make_webfonts.py       # Web 用サブセットと CSS
python scripts/make_preview.py        # preview/index.html
python scripts/verify.py              # fontTools / ots / HarfBuzz / FreeType / FontBakery → reports/verification.md
python scripts/lab.py --set KANJI_PARAMS.r_convex=24   # 少数の文字でパラメータ試作（数秒）
```

FontForge は不要です（fontTools + skia-pathops だけで動きます）。

パイプライン：`lovelyserif/build.py`
1. Noto Serif JP を対象文字＋必要な OpenType 機能でサブセット（`fontTools.subset`、グリフ名を `uniXXXX` / `.vert` などに改名）
2. Nanum Myeongjo のラテンを TrueType → 3次ベジェに変換、縮小、重なり除去
3. 組み立て（ラテン置換、全角英数合成、Nanum のカーニング移植）
4. デザインパス（手作業編集 → 接線平滑化 → 角の丸め → ラテンの太さ補正 → 整数化・縮退セグメント除去）
5. OTF（CFF）／TTF（cu2qu で2次ベジェ化、`gasp`・`prep` 付き）／WOFF2／UFO を生成、GSUB/GPOS/GDEF/BASE/vmtx を移植
6. レポート生成

## 品質検証

* 輪郭 QA（`scripts/qa.py`）：全 10,374 グリフを元フォントと比較。自己交差・縮退セグメント・輪郭の向き・消失は 0 件。丸めで自己交差しそうな字は自動で半径を下げて再処理します。
* 字間：Latin 2,500 ペアで元の Nanum に無い衝突は 0 件。
* TTF と OTF の形状一致（cu2qu 誤差 1 unit 以内）。
* 常用漢字 2,136 字：フル版・軽量版（-std）とも全収録。

`reports/verification.md` を参照。

* fontTools：全テーブルの読込・再コンパイル OK
* OpenType Sanitizer（ots）：OTF / TTF / WOFF2 すべて clean
* HarfBuzz：vert（縦組み字形）、palt、kern、fwid の動作確認
* FreeType（PIL）／Chromium：横書き・縦書き・混植の表示確認（`docs/screenshots/`）
* FontBakery universal profile：FAIL 0（WARN はファイルサイズ・post format 3・chws 未搭載など）
* macOS Font Book 向けの名前・メタデータ（nameID 1/2/4/6、日本語ローカライズ名、fsType 0、OFL 表記）

## 残る課題

* **ウェイト**：v0.1 は Regular のみ。Light / Medium / SemiBold / Bold は、Noto Serif JP の可変軸と Nanum Myeongjo Bold を元に別途設計予定（単純な太さ変更では完成扱いにしません）。
* 中欧系のラテン（Č Š Ž Ő Ğ Ş など）は未収録。表示は CSS の次のフォントに回ります。
* 「ゑ」「ヱ」「ヹ」「㋽」は意図的に収録していません（`lovelyserif/config.py` の `EXCLUDE_CODEPOINTS`）。
* ヒンティング無し（macOS / iOS / Chrome / Safari は問題なし。Windows の小サイズではやや粗く見えることがあります）。
* ラテンのカーニングは Nanum の 55 ペアのみ。
* 手作業編集は代表文字のみ。その他はアルゴリズム（角の丸め・平滑化・太さ補正）による自動調整。一覧は `reports/glyph_status.md`。
* IVS（異体字セレクタ）は未収録。

## ライセンス

Lovely Serif は [SIL Open Font License 1.1](LICENSE) で配布します。
元フォントの著作権表示を保持しています（`licenses/OFL-NanumMyeongjo.txt`、`licenses/OFL-NotoSerifCJK.txt`）。
Nanum / Noto / Source は Reserved Font Name のため、派生版の名称には使用していません。
