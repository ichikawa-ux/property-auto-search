/**
 * 物件検索条件 Googleフォーム 自動作成スクリプト
 *
 * 【初回】createForm() を実行
 * 【再作成・更新】recreateForm() を実行
 *   → 旧「検索条件」シートを「検索条件_旧」にリネームして新フォームを作成します
 */

var SPREADSHEET_ID = "1BaqjE2U6FRqnTgU03tbOy6hMevTXVOVOT078qFa5sxk";

// ─────────────────────────────────────────────────────────
// フォームを再作成（既存フォームを新しい構成に更新する場合）
// ─────────────────────────────────────────────────────────
function recreateForm() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);

  // 旧「検索条件」シートを退避
  var oldSheet = ss.getSheetByName("検索条件");
  if (oldSheet) {
    oldSheet.setName("検索条件_旧");
    Logger.log("旧シートを「検索条件_旧」にリネームしました（データ移行後に削除してください）");
  }

  _buildAndLinkForm(ss);
}

// ─────────────────────────────────────────────────────────
// 初回作成（検索条件シートがまだない場合）
// ─────────────────────────────────────────────────────────
function createForm() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  _buildAndLinkForm(ss);
}

// ─────────────────────────────────────────────────────────
// フォーム本体を構築してスプレッドシートに連携
// ─────────────────────────────────────────────────────────
function _buildAndLinkForm(ss) {
  var form = FormApp.create("物件検索条件 登録フォーム");
  form.setDescription(
    "物件の自動監視条件を登録します。\n" +
    "登録後、次の定期実行（毎時）から反映されます。"
  );
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);

  // ── 1. 担当者名 ──
  form.addTextItem()
    .setTitle("担当者名")
    .setRequired(true);

  // ── 2. メールアドレス ──
  form.addTextItem()
    .setTitle("メールアドレス")
    .setHelpText("新着物件の通知を受け取るメールアドレスを入力してください")
    .setRequired(true);

  // ── 3. 対象サイト ──
  var sitesItem = form.addCheckboxItem();
  sitesItem
    .setTitle("サイト")
    .setHelpText("巡回するサイトを選択（複数選択可）")
    .setChoices([
      sitesItem.createChoice("SUUMO"),
      sitesItem.createChoice("HOME'S"),
      sitesItem.createChoice("アットホーム"),
    ])
    .setRequired(true);

  // ── 4. エリア（地域別グループに分けて選びやすく） ──────────────
  form.addSectionHeaderItem()
    .setTitle("▼ エリア（複数区選択可・複数グループをまたいでもOK）");

  var areaCenter = form.addCheckboxItem();
  areaCenter
    .setTitle("エリア（都心）")
    .setChoices([
      areaCenter.createChoice("千代田区"),
      areaCenter.createChoice("中央区"),
      areaCenter.createChoice("港区"),
      areaCenter.createChoice("新宿区"),
      areaCenter.createChoice("文京区"),
    ]);

  var areaWest = form.addCheckboxItem();
  areaWest
    .setTitle("エリア（副都心・西部）")
    .setChoices([
      areaWest.createChoice("渋谷区"),
      areaWest.createChoice("中野区"),
      areaWest.createChoice("杉並区"),
      areaWest.createChoice("練馬区"),
      areaWest.createChoice("豊島区"),
    ]);

  var areaNorth = form.addCheckboxItem();
  areaNorth
    .setTitle("エリア（北部・城北）")
    .setChoices([
      areaNorth.createChoice("北区"),
      areaNorth.createChoice("荒川区"),
      areaNorth.createChoice("板橋区"),
      areaNorth.createChoice("足立区"),
      areaNorth.createChoice("葛飾区"),
    ]);

  var areaEast = form.addCheckboxItem();
  areaEast
    .setTitle("エリア（東部・下町）")
    .setChoices([
      areaEast.createChoice("台東区"),
      areaEast.createChoice("墨田区"),
      areaEast.createChoice("江東区"),
      areaEast.createChoice("江戸川区"),
    ]);

  var areaSouth = form.addCheckboxItem();
  areaSouth
    .setTitle("エリア（南部・城南）")
    .setChoices([
      areaSouth.createChoice("品川区"),
      areaSouth.createChoice("目黒区"),
      areaSouth.createChoice("大田区"),
      areaSouth.createChoice("世田谷区"),
    ]);

  // ── 5. 家賃上限（小数対応：8.5 = 85,000円） ──────────────────
  form.addSectionHeaderItem().setTitle("▼ 希望条件");

  form.addTextItem()
    .setTitle("家賃上限（万円）")
    .setHelpText("例: 15 → 15万円以下　8.5 → 85,000円以下（小数も入力可）")
    .setRequired(true);

  // ── 6. 間取り（タイプ × 部屋数で組み合わせ指定） ───────────────
  var layoutType = form.addCheckboxItem();
  layoutType
    .setTitle("間取タイプ")
    .setHelpText("例：1LDKを探す場合は「LDK」を選択 / 未選択=すべて対象")
    .setChoices([
      layoutType.createChoice("ワンルーム"),
      layoutType.createChoice("K（キッチン）"),
      layoutType.createChoice("DK（ダイニングキッチン）"),
      layoutType.createChoice("SDK（サービスルーム＋DK）"),
      layoutType.createChoice("LDK（リビングダイニングキッチン）"),
      layoutType.createChoice("SLDK（サービスルーム＋LDK）"),
    ])
    .setRequired(false);

  var roomCount = form.addCheckboxItem();
  roomCount
    .setTitle("間取部屋数")
    .setHelpText("例：1LDKを探す場合は「1室」を選択 / 未選択=すべての部屋数対象")
    .setChoices([
      roomCount.createChoice("1室"),
      roomCount.createChoice("2室"),
      roomCount.createChoice("3室"),
      roomCount.createChoice("4室以上"),
    ])
    .setRequired(false);

  // ── 7. 築年数上限 ──
  form.addTextItem()
    .setTitle("築年数上限（年）")
    .setHelpText("例: 20 → 築20年以内。空白=制限なし")
    .setRequired(false);

  // ── 8. 駅徒歩上限 ──
  form.addTextItem()
    .setTitle("駅徒歩上限（分）")
    .setHelpText("例: 10 → 最寄り駅から徒歩10分以内。空白=制限なし")
    .setRequired(false);

  // ── 9. BT別 ──
  var btItem = form.addMultipleChoiceItem();
  btItem
    .setTitle("BT別（バストイレ別）")
    .setChoices([
      btItem.createChoice("必須"),
      btItem.createChoice("どちらでも"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 10. 独立洗面台 ──
  var washstandItem = form.addMultipleChoiceItem();
  washstandItem
    .setTitle("独立洗面台")
    .setChoices([
      washstandItem.createChoice("必須"),
      washstandItem.createChoice("どちらでも"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 11. ペット ──
  var petItem = form.addMultipleChoiceItem();
  petItem
    .setTitle("ペット")
    .setHelpText("「可・相談可を含む」→ ペット可＋相談可の両方を検索")
    .setChoices([
      petItem.createChoice("可・相談可を含む"),
      petItem.createChoice("不可のみ"),
      petItem.createChoice("問わない"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 12. 最低階数 ──
  form.addTextItem()
    .setTitle("最低階数（階以上）")
    .setHelpText("例: 2 → 2階以上。空白=1階も含む")
    .setRequired(false);

  // ── スプレッドシートと連携 ──
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  Utilities.sleep(3000);

  // 新しく作られたシートを「検索条件」にリネーム
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName().indexOf("フォームの回答") !== -1) {
      sheets[i].setName("検索条件");
      Logger.log("新シートを「検索条件」にリネームしました");
      break;
    }
  }

  Logger.log("✅ フォーム作成完了！");
  Logger.log("フォームURL（担当者に共有）: " + form.getPublishedUrl());
  Logger.log("フォーム編集URL: " + form.getEditUrl());
}
