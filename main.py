from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from servise import *
from connection import *
from datetime import datetime
import asyncio
import os

load_dotenv()

token = os.getenv("BOT_TOKEN")

bot = Bot(token=token)
dp = Dispatcher()


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Add Task")],
        [KeyboardButton(text="My Tasks")],
        [KeyboardButton(text="Update Task")],
        [KeyboardButton(text="Delete Task")],
        [KeyboardButton(text="Help")],
    ],
    resize_keyboard=True,
)



class AddTask(StatesGroup):
    title = State()
    caption = State()
    due_date = State()


class UpdateTask(StatesGroup):
    task_id = State()
    title = State()
    caption = State()
    due_date = State()


class DeleteTask(StatesGroup):
    task_id = State()



@dp.message(CommandStart())
async def start_bot(message: Message):
    user = message.from_user
    await get_user_by_id(user.id)
    await message.answer(
        f"Hello, {user.full_name}!",reply_markup=main_kb)



@dp.message(F.text == "Help")
@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(f"""
Task Manager Bot

/start - Start the bot
/help - Show help

Add Task - Create a task
My Tasks - View your tasks
Update Task - Edit a task
Delete Task - Delete a task
    """)





@dp.message(F.text == "Add Task")
@dp.message(Command("add_task"))
async def add_task_start(message: Message, state: FSMContext):
    await message.answer("Enter task title:")
    await state.set_state(AddTask.title)




@dp.message(AddTask.title)
async def add_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Enter task description: ")
    await state.set_state(AddTask.caption)




@dp.message(AddTask.caption)
async def add_task_caption(message: Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await message.answer(f"""
Enter due date in this format:
2026-12-31 18:30
    """)
    await state.set_state(AddTask.due_date)




@dp.message(AddTask.due_date)
async def add_task_date(message: Message, state: FSMContext):
    try:
        due_date = message.text.strip()
        datetime.strptime(due_date, "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        await message.answer("""
Invalid date format.
Example: 2026-12-31 18:30
        """)
        return

    
    data = await state.get_data()
    if await create_task(data["title"],data["caption"],due_date,message.from_user.id):
        await message.answer(f"""
Task created successfully!
Title: {data['title']}
Description: {data['caption']}
Due date: {due_date}
        """)
    else:
        await message.answer("Failed to create task.")
    await state.clear()




@dp.message(F.text == "My Tasks")
@dp.message(Command("get_my_tasks"))
async def get_my_tasks(message: Message):
    tasks = await get_task_by_id(message.from_user.id)

    if not tasks:
        await message.answer("You have no tasks yet.")
        return

    for task in tasks:
        await message.answer(f"""
ID: {task['task_id']}
Title: {task['title']}
Description: {task['caption']}
Due date: {task['due_date']}
Status: {task['status']}
Created at: {task['created_at']}
        """)



@dp.message(F.text == "Update Task")
@dp.message(Command("update_task"))
async def update_task_start(message: Message, state: FSMContext):
    await message.answer("Enter the ID of the task to update:")
    await state.set_state(UpdateTask.task_id)




@dp.message(UpdateTask.task_id)
async def update_task_id(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Task ID must be a number.")
        return

    task_id = int(message.text)
    tasks = await get_task_by_id(message.from_user.id)
    if not tasks or not any(task["task_id"] == task_id for task in tasks):
        await message.answer("Task not found.")
        await state.clear()
        return
    await state.update_data(task_id=task_id)
    await message.answer("Enter the new title:")
    await state.set_state(UpdateTask.title)




@dp.message(UpdateTask.title)
async def update_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Enter the new description:")
    await state.set_state(UpdateTask.caption)




@dp.message(UpdateTask.caption)
async def update_task_caption(message: Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await message.answer(f"""
Enter the new due date:
2026-12-31 18:30
    """)
    await state.set_state(UpdateTask.due_date)



@dp.message(UpdateTask.due_date)
async def update_task_date(message: Message, state: FSMContext):
    try:
        due_date = message.text.strip()
        datetime.strptime(due_date, "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        await message.answer("""
Invalid date format.
Example: 2026-12-31 18:30
        """)
        return

    data = await state.get_data()
    if await update_task_db(data["task_id"],data["title"],data["caption"],due_date,message.from_user.id):
        await message.answer("Task updated successfully!")
    else:
        await message.answer("Task could not be updated.")
    await state.clear()






@dp.message(Command("delete_task"))
@dp.message(F.text == "Delete Task")
async def delete_task_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Enter the ID of the task to delete:")
    await state.set_state(DeleteTask.task_id)




@dp.message(DeleteTask.task_id)
async def delete_task_finish(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer("Task ID must be a number.")
        return

    task_id = int(message.text)
    tasks = await get_task_by_id(message.from_user.id)
    if not tasks or not any(task["task_id"] == task_id for task in tasks):
        await message.answer("Task not found")
        await state.clear()
        return
    if await delete_task_db(task_id,message.from_user.id):
        await message.answer(
            "Task deleted successfully!"
        )
    else:
        await message.answer("Task not found")
    await state.clear()



async def main():
    await create_table()
    print("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
