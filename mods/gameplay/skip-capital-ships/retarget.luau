-- TARGET NEAREST ENEMY, without the capital ships: the game's side.
--
-- When the player script (nearest.luau) hears the key, this global script makes the nearest hostile
-- that isn't a capital ship the player's target, within the reach of the game's key. With none in
-- reach, the game's own choice stands, so a lone capital ship can still be targeted.
local world = require("openreliant.world")

-- How far the game's nearest target keys look: twice its picking range (hud.zig, pick_reach).
local reach = 2 * 330000

-- Whether `object` is what the key is for: a hostile that isn't a capital ship, which the game's
-- key could take too, so neither exploding nor cloaked.
local function wanted(object)
    return object.side == "hostile" and object.class ~= "capital"
        and not object.exploding and not object.cloaked
end

-- The wanted hostiles within reach of the player, nearest first.
local function candidates()
    local player = world.player
    local found = {}
    for _, object in world.objects() do
        if not object.is_player and wanted(object) then
            local apart = vector.magnitude(object.position - player.position)
            if apart < reach then
                table.insert(found, { object = object, apart = apart })
            end
        end
    end
    table.sort(found, function(a, b)
        return a.apart < b.apart
    end)
    return found
end

-- Makes the nearest wanted hostile the player's target, skipping any the player can't aim at.
-- Returns whether it found one.
local function retarget()
    if not world.player then
        return false
    end
    for _, candidate in candidates() do
        if world.set_player_target(candidate.object) then
            return true
        end
    end
    return false
end

return {
    event_handlers = {
        SkipCapitalShipsRetarget = function()
            retarget()
        end,
    },
}
