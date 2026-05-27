/**
 * 物件監視システム — Google Apps Script Webアプリ
 *
 * 【デプロイ手順】
 *  1. スプレッドシートを開く → 拡張機能 → Apps Script
 *  2. 左ペインでファイル追加 → スクリプト → ファイル名「web_app」
 *  3. このコードを貼り付けて保存（Ctrl+S）
 *  4. 関数「setupProperties」を選択して「実行」→ 初回はアクセス許可を承認
 *  5. デプロイ → 新しいデプロイ
 *       種類: ウェブアプリ
 *       次のユーザーとして実行: 自分（ichikawa@s-table.co.jp）
 *       アクセスできるユーザー: 全員
 *     → デプロイ → ウェブアプリURLをコピー
 *  6. GitHub → Settings → Secrets → SHEETS_WEB_APP_URL にURLを貼り付け
 */

var SPREADSHEET_ID = "1BaqjE2U6FRqnTgU03tbOy6hMevTXVOVOT078qFa5sxk";
var SHEET_NAME = "検索条件";

/**
 * ★ 初回のみ実行★
 * GitHub Secrets の SHEETS_WEB_APP_TOKEN と同じ値をここに貼り付けてから実行する
 */
function setupProperties() {
  PropertiesService.getScriptProperties().setProperty(
    "SECRET_TOKEN",
    "vNFTAk8z7Iuqpa39BfYycjU0RKSdL4b6sGg1MoEV"
  );
  Logger.log("SECRET_TOKEN を設定しました");
}

/**
 * Webアプリのエントリポイント
 * GET ?token=xxxx でアクセスするとスプレッドシートのデータをJSONで返す
 */
function doGet(e) {
  try {
    // トークン認証
    var props    = PropertiesService.getScriptProperties();
    var expected = props.getProperty("SECRET_TOKEN");
    var received = e && e.parameter ? e.parameter.token : "";

    if (!expected || received !== expected) {
      return _json({ error: "Unauthorized" });
    }

    // スプレッドシート読み込み
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    var ws = ss.getSheetByName(SHEET_NAME);

    if (!ws) {
      return _json({ error: "Sheet not found: " + SHEET_NAME, rows: [] });
    }

    var data = ws.getDataRange().getValues();
    if (data.length <= 1) {
      return _json({ rows: [] });
    }

    var headers = data[0].map(String);
    var rows    = [];

    for (var i = 1; i < data.length; i++) {
      var row = {};
      for (var j = 0; j < headers.length; j++) {
        var v = data[i][j];
        // Dateオブジェクトを文字列に変換（タイムスタンプ列など）
        if (v instanceof Date) {
          v = Utilities.formatDate(v, "Asia/Tokyo", "yyyy-MM-dd HH:mm:ss");
        }
        row[headers[j]] = v;
      }
      rows.push(row);
    }

    return _json({ rows: rows });

  } catch (err) {
    return _json({ error: err.toString() });
  }
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
