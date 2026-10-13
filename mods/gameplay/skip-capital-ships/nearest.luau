-- TARGET NEAREST ENEMY, without the capital ships: the player's side.
--
-- The game's key takes the nearest hostile ship of any class, so a capital ship alongside the
-- player wins over the fighter or the torpedo just behind it. This player script hears the key,
-- where the game's key does something, and asks the global script (retarget.luau) to pick again
-- among the hostiles that aren't capital ships. Player scripts can't change the game themselves;
-- the event reaches the global script at the next update, so the game's choice shows for a frame
-- at most before the mod's replaces it.
local core = require("openreliant.core")
local camera = require("openreliant.camera")
local self = require("openreliant.self")

-- The views the game's key works from.
local views = { cockpit = true, chase = true }

return {
    engine_handlers = {
        on_action = function(action)
            if action ~= "target_nearest_enemy" then
                return
            end
            -- Only where the game's key does something: on Player Control, from the cockpit or
            -- the chase view.
            if not self or self.order ~= "player_control" or not views[camera.view] then
                return
            end
            core.send_global_event("SkipCapitalShipsRetarget", {})
        end,
    },
}
