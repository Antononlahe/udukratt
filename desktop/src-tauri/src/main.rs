#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::io::Read;
use tauri_plugin_dialog::DialogExt;

/// Extract plain text from a .docx (paragraph per line). Runs locally, no network.
#[tauri::command]
fn docx_text(bytes: Vec<u8>) -> Result<String, String> {
    let mut z = zip::ZipArchive::new(std::io::Cursor::new(bytes)).map_err(|e| e.to_string())?;
    let mut xml = String::new();
    z.by_name("word/document.xml").map_err(|e| e.to_string())?.read_to_string(&mut xml).map_err(|e| e.to_string())?;
    let xml = xml.replace("</w:p>", "\n").replace("<w:tab/>", "\t").replace("<w:br/>", "\n");
    let (mut out, mut tag) = (String::new(), false);
    for c in xml.chars() { match c { '<' => tag = true, '>' => tag = false, _ if !tag => out.push(c), _ => {} } }
    Ok(out.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&apos;", "'").replace("&amp;", "&"))
}

/// Ask where to save and write the redacted text. Returns the path, or None if cancelled.
#[tauri::command]
async fn save_text(app: tauri::AppHandle, suggested: String, text: String) -> Result<Option<String>, String> {
    if let Ok(p) = std::env::var("UDUKRATT_SAVE_TO") { // headless smoke test hook
        std::fs::write(&p, text).map_err(|e| e.to_string())?;
        if std::env::var("UDUKRATT_SMOKE_IN").is_ok() { app.exit(0); }
        return Ok(Some(p));
    }
    let Some(fp) = app.dialog().file().set_file_name(&suggested).blocking_save_file() else { return Ok(None) };
    let p = fp.into_path().map_err(|e| e.to_string())?;
    std::fs::write(&p, text).map_err(|e| e.to_string())?;
    Ok(Some(p.display().to_string()))
}

/// Headless smoke test hook: returns (file name, contents) of UDUKRATT_SMOKE_IN, if set.
#[tauri::command]
fn smoke_input() -> Option<(String, String)> {
    let p = std::env::var("UDUKRATT_SMOKE_IN").ok()?;
    let name = std::path::Path::new(&p).file_name()?.to_string_lossy().into_owned();
    Some((name, std::fs::read_to_string(&p).ok()?))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![docx_text, save_text, smoke_input])
        .run(tauri::generate_context!())
        .expect("error while running Udukratt");
}
