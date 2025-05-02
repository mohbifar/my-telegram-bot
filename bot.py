import os
import re
import tempfile
import yt_dlp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# تنظیمات ربات
TOKEN = "8026272499:AAFcLf2IovB6tQkWSH7wTkLLWOSu4PEtN34"
CHANNEL_ID = -1002637620980  # کانال "ماجراجویی‌های ورزشی"
BOT_USERNAME = "@MyAutoPost1_Bot"  # یوزرنیم صحیح ربات
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB محدودیت تلگرام
ADMIN_IDS = [123456789]  # آیدی عددی ادمین‌ها (جایگزین کنید)

async def download_video(url: str) -> tuple:
    """دانلود ویدیو و بازگرداندن اطلاعات و مسیر فایل"""
    temp_dir = tempfile.mkdtemp(prefix="ytdl_")
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'max_filesize': MAX_FILE_SIZE,
        'writethumbnail': True,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            
            if os.path.getsize(filepath) > MAX_FILE_SIZE:
                raise ValueError("حجم ویدیو بیش از حد مجاز است (50MB)")
                
            return True, info, filepath
    except yt_dlp.utils.DownloadError as e:
        return False, f"خطا در دانلود: {str(e)}", None
    except Exception as e:
        return False, f"خطای ناشناخته: {str(e)}", None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.message.from_user
    url = update.message.text.strip()
    
    # بررسی ادمین بودن کاربر (اختیاری)
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ دسترسی محدود شده است")
        return

    # بررسی لینک معتبر یوتیوب
    if not re.match(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+', url):
        await update.message.reply_text("❌ لطفاً فقط لینک یوتیوب ارسال کنید")
        return

    try:
        status_msg = await update.message.reply_text("⏳ در حال پردازش لینک...")
        
        success, result, filepath = await download_video(url)
        
        if not success:
            await status_msg.edit_text(f"❌ {result}")
            return

        info, filepath = result
        title = info.get('title', 'ویدیو')
        duration = info.get('duration', 0)
        
        await status_msg.edit_text(f"📥 دانلود کامل شد!\nعنوان: {title}\n⏳ در حال آپلود به کانال...")

        # ارسال ویدیو به کانال
        with open(filepath, 'rb') as video_file:
            caption = (
                f"🎬 {title}\n\n"
                f"⏳ مدت زمان: {duration//60}:{duration%60:02d}\n"
                f"📤 ارسال شده توسط: @{user.username if user.username else user.first_name}\n"
                f"🤖 @{BOT_USERNAME}"
            )
            
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=video_file,
                caption=caption,
                supports_streaming=True,
                timeout=300,
                width=info.get('width'),
                height=info.get('height'),
                duration=duration,
            )
        
        await status_msg.edit_text(f"✅ ویدیو با موفقیت به کانال ارسال شد\n\nعنوان: {title}")
    
    except Exception as e:
        error_msg = f"❌ خطا در پردازش ویدیو: {str(e)}"
        print(error_msg)
        await status_msg.edit_text(error_msg)
    
    finally:
        # پاکسازی فایل‌های موقت
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            thumb_path = os.path.splitext(filepath)[0] + ".webp"
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            temp_dir = os.path.dirname(filepath)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"""
    🤖 ربات فعال شد!
    نام ربات: {BOT_USERNAME}
    کانال مقصد: {CHANNEL_ID}
    در حال انتظار برای لینک‌ها...
    """)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
