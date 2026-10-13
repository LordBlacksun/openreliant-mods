-- Homing Screamers: the player's own Screamers home on the player's target, as the AI's do.
--
-- Outside a multiplayer game, the game flies the player's Screamers straight and lights no missile
-- warning for them (OpenReliant's src/engine/game/missiles.zig, `homesAtLaunch`; the original's
-- `missile_order_screamer`, 0x00497F10, and `missiles_update`, 0x004960F0). The player's Screamer
-- also leaves with the player's target only while the display holds a lock, and with no target
-- otherwise (src/engine/input.zig, `launchMissile`).
--
-- This missile script runs on every missile and leaves all but the player's Screamers alone. Each
-- of those takes the player's target as it leaves its pod, locked or not, and the script sets its
-- `homes`. From then on the game guides it as it guides the AI's Screamers (missiles.zig, `home`):
-- its target gets a missile warning, a decoy can draw it off, and it ends once its target is lost.
--
-- Where the player has no target, or one `aimable` rules out, the Screamer flies straight as
-- before, since the game's guidance would end it as soon as its pod launch is over.

local self = require("openreliant.self")

-- A pod that has launched its last Screamer is jettisoned through the same launch, as a missile
-- of its type pushed 50 along its own Y axis, which points down (missiles.zig, `setOrder` and
-- `jettison_drop`); a Screamer leaves at its launcher's velocity (`spawn`). More than half that
-- push is a pod.
local JETTISON_PUSH = 25

-- Whether `object`, or its component where `component` names one, is still one to aim at, as the
-- AI judges it (src/engine/game/ai.zig, `target_barred` and `ValidTarget`): the object not
-- exploding, cloaked, disabled or ejected, and targetable, and the component not destroyed. The AI
-- won't aim at a ship sent off or a hidden component either, but a script can't see those, so the
-- game ends a Screamer aimed at one as its pod launch is over.
local function aimable(object, component)
    if not (object ~= nil and object:is_valid() and not object.exploding and not object.cloaked
        and not object.disabled and not object.ejected and object.targetable) then
        return false
    end
    if component == nil then return true end
    for _, part in object:parts() do
        if part.component == component then return not part.destroyed end
    end
    return false
end

return {
    engine_handlers = {
        on_added = function()
            if self.type ~= "screamer" then return end
            local launcher = self.launcher
            if launcher == nil or not launcher.is_player then return end
            if vector.dot(self.velocity - launcher.velocity, self.orientation.down) > JETTISON_PUSH then return end
            local aimed = launcher.target
            if aimed == nil or aimed.object == launcher then return end
            if not aimable(aimed.object, aimed.component) then return end
            self.target = { object = aimed.object, component = aimed.component }
            self.homes = true
        end,
    },
}
