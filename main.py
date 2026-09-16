import asyncio

# pygbag scans this file's imports to decide what to load into the browser VM,
# so pygame must be imported here at the top level even though it looks unused.
import pygame  # noqa: F401


async def main():
    # Let the loader finish setting up (in the browser pygame is only usable
    # once the code has yielded control at least once).
    await asyncio.sleep(0)
    from zombietrees.game import Game

    await Game().run()


if __name__ == "__main__":
    asyncio.run(main())
