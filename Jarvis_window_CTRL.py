import os
import subprocess
import logging
import sys
import asyncio
from fuzzywuzzy import process

try:
    import pygetwindow as gw
except ImportError:
    gw = None

from langchain.tools import tool


sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



APP_MAPPINGS = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "finder": "Finder",
    "vlc": "VLC",
    "textedit": "TextEdit",
    "notes": "Notes",
    "calculator": "Calculator",
    "spotify": "Spotify",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
}



async def focus_app(app_name: str) -> bool:
    """Brings an app to the foreground using AppleScript"""
    try:
        subprocess.call([
            "osascript", "-e",
            f'tell application "{app_name}" to activate'
        ])
        return True
    except Exception as e:
        logger.error(f"❌ Could not activate {app_name}: {e}")
        return False




async def index_items(base_dirs):
    item_index = []

    for base_dir in base_dirs:
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                item_index.append({"name": d, "path": os.path.join(root, d), "type": "folder"})
            for f in files:
                item_index.append({"name": f, "path": os.path.join(root, f), "type": "file"})

    logger.info(f"✅ Indexed {len(item_index)} items.")
    return item_index


async def search_item(query, index, item_type):
    filtered = [item for item in index if item["type"] == item_type]
    choices = [item["name"] for item in filtered]

    if not choices:
        return None

    best_match, score = process.extractOne(query, choices)
    logger.info(f"🔍 Matched '{query}' to '{best_match}' (score {score})")

    if score > 70:
        return next((item for item in filtered if item["name"] == best_match), None)

    return None





async def open_folder(path):
    try:
        subprocess.call(["open", path])
        await asyncio.sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"❌ Folder open error: {e}")
        return False


async def play_file(path):
    try:
        subprocess.call(["open", path])
        await asyncio.sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"❌ File open error: {e}")
        return False


async def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"📁 Folder created: {path}"
    except Exception as e:
        return f"❌ Error creating folder: {e}"


async def rename_item(old_path, new_path):
    try:
        os.rename(old_path, new_path)
        return f"✏️ Renamed to: {new_path}"
    except Exception as e:
        return f"❌ Rename failed: {e}"


async def delete_item(path):
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        return f"🗑️ Deleted: {path}"
    except Exception as e:
        return f"❌ Delete failed: {e}"




@tool
async def open_app(app_title: str) -> str:
    """Opens desktop apps on macOS"""

    app_title = app_title.lower().strip()
    app_name = APP_MAPPINGS.get(app_title, app_title)

    try:
        subprocess.call(["open", "-a", app_name])
        await asyncio.sleep(1)
        await focus_app(app_name)
        return f"🚀 App launched: {app_name}"
    except Exception as e:
        return f"❌ App launch failed: {e}"


@tool
async def close_app(app_title: str) -> str:
    """Closes macOS applications"""

    app_title = app_title.lower().strip()
    app_name = APP_MAPPINGS.get(app_title, app_title)

    try:
        subprocess.call([
            "osascript", "-e",
            f'tell application "{app_name}" to quit'
        ])
        return f"🛑 App closed: {app_name}"
    except Exception as e:
        return f"❌ Close failed: {e}"




@tool
async def folder_file(command: str) -> str:
    """Natural language to perform file/folder actions"""

    folders_to_index = ["/Users/bikash"]
    index = await index_items(folders_to_index)
    command_lower = command.lower()

    if "create folder" in command_lower:
        name = command.replace("create folder", "").strip()
        path = os.path.join("/Users/bikash", name)
        return await create_folder(path)

    if "rename" in command_lower:
        parts = command_lower.replace("rename", "").strip().split("to")
        if len(parts) == 2:
            old_name, new_name = [x.strip() for x in parts]
            item = await search_item(old_name, index, "folder") or await search_item(old_name, index, "file")
            if item:
                new_path = os.path.join(os.path.dirname(item["path"]), new_name)
                return await rename_item(item["path"], new_path)
        return "❌ Invalid rename command."

    if "delete" in command_lower:
        item = await search_item(command, index, "folder") or await search_item(command, index, "file")
        if item:
            return await delete_item(item["path"])
        return "❌ Item not found for delete."

    if "folder" in command_lower:
        item = await search_item(command, index, "folder")
        if item:
            await open_folder(item["path"])
            return f"📂 Folder opened: {item['name']}"
        return "❌ Folder not found."

    item = await search_item(command, index, "file")
    if item:
        await play_file(item["path"])
        return f"📄 File opened: {item['name']}"

    return "⚠ No match found."
