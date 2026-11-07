import unittest
from game.core.headless_server import HeadlessGameServer
from game.models.state import CardState

class TestPppopipupuSpar(unittest.TestCase):
    def test_spar_awakening_flow(self):
        plugin = HeadlessGameServer()
        router = plugin.cli_router
        save_manager = plugin.save_manager

        user_id = "test_spar_user"
        save_manager.delete_save(user_id)
        stats = save_manager.load_stats(user_id)
        stats.player_name = "测试玩家"
        stats.in_town = True
        stats.town_pos = "range"
        save_manager.save_stats(user_id, stats)

        def send(cmd):
            parts = cmd.split()
            res_list = list(router.handle_command(user_id, parts))
            return "\n".join(res_list)

        res1 = send("talk pppopipupu")
        print("Talk response:\n", res1)

        res2 = send("2")
        print("Challenge response:\n", res2)

        run = save_manager.load_save(user_id)
        run.player.hand = [CardState(id="fire_bolt")]
        run.player.actions = 3
        run.player.bonus_actions = 3
        save_manager.save_save(user_id, run)

        run = save_manager.load_save(user_id)
        print("Before attack enemies:")
        for e in run.enemies:
            print(f"Name: {e.name}, HP: {e.hp}")

        res3 = send("使用 1 e1")
        print("Use spell response:\n", res3)

        res4 = send("e")
        print("End turn response:\n", res4)

        run_after = save_manager.load_save(user_id)
        if run_after:
            print("After enemy turn:")
            for e in run_after.enemies:
                print(f"Name: {e.name}, HP: {e.hp}")
        else:
            print("Game ended, no save found.")

if __name__ == "__main__":
    unittest.main()
