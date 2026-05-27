/**
 * 物件検索条件 Googleフォーム 自動作成スクリプト
 *
 * 使い方:
 *  1. Googleスプレッドシートを開く
 *  2. 拡張機能 → Apps Script
 *  3. このコードを貼り付けて保存
 *  4. SPREADSHEET_ID を自分のスプレッドシートIDに書き換える
 *  5. 「createForm」を選択して「実行」ボタンを押す
 *  6. ログに表示されたフォームURLを担当者に共有する
 */

// ★ここを書き換えてください★
var SPREADSHEET_ID = "あなたのスプレッドシートIDをここに入力";

function createForm() {
  // フォーム作成
  var form = FormApp.create("物件検索条件 登録フォーム");
  form.setDescription(
    "物件の自動監視条件を登録します。\n" +
    "登録後、次の定期実行（毎時）から反映されます。\n\n" +
    "⚠ 条件を削除・無効にしたい場合はスプレッドシートで「有効」列をFALSEに変更してください。"
  );
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);

  // ── 1. 担当者名 ──────────────────────────────────
  form.addTextItem()
    .setTitle("担当者名")
    .setRequired(true);

  // ── 2. メールアドレス ──────────────────────────────
  form.addTextItem()
    .setTitle("メールアドレス")
    .setHelpText("新着物件の通知を受け取るメールアドレスを入力してください")
    .setRequired(true);

  // ── 3. 対象サイト ──────────────────────────────────
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

  // ── 4. エリア ────────────────────────────────────
  var areaItem = form.addCheckboxItem();
  areaItem
    .setTitle("エリア")
    .setHelpText("監視するエリアを選択（複数選択可）※現在は東京23区のみ対応")
    .setChoices([
      areaItem.createChoice("千代田区"),
      areaItem.createChoice("中央区"),
      areaItem.createChoice("港区"),
      areaItem.createChoice("新宿区"),
      areaItem.createChoice("文京区"),
      areaItem.createChoice("台東区"),
      areaItem.createChoice("墨田区"),
      areaItem.createChoice("江東区"),
      areaItem.createChoice("品川区"),
      areaItem.createChoice("目黒区"),
      areaItem.createChoice("大田区"),
      areaItem.createChoice("世田谷区"),
      areaItem.createChoice("渋谷区"),
      areaItem.createChoice("中野区"),
      areaItem.createChoice("杉並区"),
      areaItem.createChoice("豊島区"),
      areaItem.createChoice("北区"),
      areaItem.createChoice("荒川区"),
      areaItem.createChoice("板橋区"),
      areaItem.createChoice("練馬区"),
      areaItem.createChoice("足立区"),
      areaItem.createChoice("葛飾区"),
      areaItem.createChoice("江戸川区"),
    ])
    .setRequired(true);

  // ── 5. 家賃上限 ──────────────────────────────────
  form.addTextItem()
    .setTitle("家賃上限（万円）")
    .setHelpText("例: 15　→　15万円以下の物件を通知します")
    .setRequired(true);

  // ── 6. 間取り ────────────────────────────────────
  var layoutItem = form.addCheckboxItem();
  layoutItem
    .setTitle("間取り")
    .setHelpText("対象にする間取りを選択（未選択の場合はすべて対象）")
    .setChoices([
      layoutItem.createChoice("1R"),
      layoutItem.createChoice("1K"),
      layoutItem.createChoice("1DK"),
      layoutItem.createChoice("1LDK"),
      layoutItem.createChoice("2K"),
      layoutItem.createChoice("2DK"),
      layoutItem.createChoice("2LDK"),
      layoutItem.createChoice("3K"),
      layoutItem.createChoice("3DK"),
      layoutItem.createChoice("3LDK"),
    ])
    .setRequired(false);

  // ── 7. 築年数上限 ────────────────────────────────
  form.addTextItem()
    .setTitle("築年数上限（年）")
    .setHelpText("例: 20　→　築20年以内。空白にすると制限なし")
    .setRequired(false);

  // ── 8. 駅徒歩上限 ────────────────────────────────
  form.addTextItem()
    .setTitle("駅徒歩上限（分）")
    .setHelpText("例: 10　→　最寄り駅から徒歩10分以内。空白にすると制限なし")
    .setRequired(false);

  // ── 9. BT別（バストイレ別）────────────────────────
  var btItem = form.addMultipleChoiceItem();
  btItem
    .setTitle("BT別（バストイレ別）")
    .setChoices([
      btItem.createChoice("必須"),
      btItem.createChoice("どちらでも"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 10. 独立洗面台 ───────────────────────────────
  var washstandItem = form.addMultipleChoiceItem();
  washstandItem
    .setTitle("独立洗面台")
    .setChoices([
      washstandItem.createChoice("必須"),
      washstandItem.createChoice("どちらでも"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 11. ペット ────────────────────────────────────
  var petItem = form.addMultipleChoiceItem();
  petItem
    .setTitle("ペット")
    .setHelpText("「可・相談可を含む」を選ぶとペット可＋相談可の両方を一度に検索します")
    .setChoices([
      petItem.createChoice("可・相談可を含む"),
      petItem.createChoice("不可のみ"),
      petItem.createChoice("問わない"),
    ])
    .showOtherOption(false)
    .setRequired(true);

  // ── 12. 階数（階以上）────────────────────────────
  form.addTextItem()
    .setTitle("最低階数（階以上）")
    .setHelpText("例: 2　→　2階以上。空白にすると制限なし（1階も含む）")
    .setRequired(false);

  // ── スプレッドシートと連携 ────────────────────────
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  // フォーム回答シートを「検索条件」にリネーム
  SpreadsheetApp.flush();
  Utilities.sleep(2000); // シートが作成されるのを待つ

  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    var name = sheets[i].getName();
    if (name.indexOf("フォームの回答") !== -1) {
      sheets[i].setName("検索条件");
      Logger.log("シートを「検索条件」にリネームしました");
      break;
    }
  }

  Logger.log("✅ フォーム作成完了！");
  Logger.log("フォームURL（担当者に共有）: " + form.getPublishedUrl());
  Logger.log("フォーム編集URL: " + form.getEditUrl());
}
