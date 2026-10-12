-- Homing Screamers: the player's own Screamers home on the player's target.
--
-- The game flies a Screamer straight when a player launched it outside a multiplayer game, and
-- homes it otherwise (OpenReliant's src/engine/game/missiles.zig, `run`; the original's
-- `missile_order_screamer`, 0x00497F10). The player's Screamer leaves with the player's target
-- only while the display holds a lock, and with no target otherwise (src/engine/input.zig,
-- `launchMissile`).
--
-- This missile script runs on every missile and leaves all but the player's Screamers alone. Each
-- of those takes the player's target as it leaves its pod, locked or not. Once its pod launch is
-- over, the script steers it every simulation step as the game steers the AI's Screamers
-- (missiles.zig, `home` and `steer`; the original's `missile_home`, 0x00496C90): it aims at the
-- target, led along the target's nose; its pitch and yaw follow the angles off that point, less
-- four times its turn so far, eased by its rate inertia; its throttle is the cosine of the angle
-- off it.
--
-- A script can't set a missile's controls, so the script keeps the turn itself and turns the
-- missile, and cuts its speed by the part of the motor's push that the throttle would hold back.
-- The game's own steering stays off for it: its rates stay 0 and its throttle 1.
--
-- It differs from the AI's Screamers in these ways:
-- - Its target gets no missile warning, as for any player's Screamer (missiles.zig, `frame`), so
--   it doesn't make the AI drop countermeasures. It doesn't follow a decoy either. A script can't
--   set either.
-- - Where the AI's Screamer ends as its target is lost, the player's flies straight on.
-- - It reaches its target later than the AI's. Unknown: why, since the steering and its numbers
--   are the same.
-- - For a Saladin, Troop Car, Kronstadt or Boridin, it aims at the ship's middle, where the AI aims
--   at a set part of it (src/engine/game/ai.zig, `targetPart`). It loses a component target when
--   the component is destroyed, but not when it's hidden.

local self = require("openreliant.self")
local records = require("openreliant.records")
local util = require("openreliant.util")

-- A missile's flight model (missiles.zig, `flightOf` and `Table.load`): its speed and its turn
-- rate are its record's; the inertias are the executable's.
local INERTIA = 0.84
local RATE_INERTIA = 0.71
-- How much of its turn so far the steering takes off its aim, and how hard it steers: fully ten
-- degrees off (missiles.zig, `rate_damping` and `steer_gain`).
local RATE_DAMPING = 4
local STEER_GAIN = 18 / math.pi
-- Beyond this the target is lost (missiles.zig, `lost_range`).
local LOST_RANGE = 1000000
-- The pod launch lasts 50 of the game's 100 ticks a second, and a simulation step is 4 ticks
-- (missiles.zig, `pod_launch_ticks`; gameobj.zig, `ticks_per_step`). The AI's guidance takes
-- over in the frame after the 13th step and first moves the missile in the 14th, so the script
-- steers from its 13th step on, whose turn the 14th step's move flies.
local POD_LAUNCH_STEPS = 12
-- A pod that has launched its last Screamer is jettisoned through the same launch, as a missile
-- of its type pushed 50 along its own Y axis, which points down (missiles.zig, `setOrder` and
-- `jettison_drop`); a Screamer leaves at its launcher's velocity (`spawn`). More than half that
-- push is a pod.
local JETTISON_PUSH = 25

local homing = false
local target = nil
local steps = 0
local pitch_rate = 0
local yaw_rate = 0
local speed = 0
local turn_rate = 0

-- Whether `object` is still one to aim at, as the AI judges it (src/engine/game/ai.zig,
-- `target_barred`): not exploding, cloaked, disabled or ejected, and targetable. A ship sent off
-- is barred too, but a script can't see that.
local function aimable(object)
    return object ~= nil and object:is_valid() and not object.exploding and not object.cloaked
        and not object.disabled and not object.ejected and object.targetable
end

-- The point the missile aims at: the target's component where it names one, else the target.
-- Nil where the component is destroyed.
local function aimedAt(object, component)
    if component ~= nil then
        for _, part in object:parts() do
            if part.component == component then
                if part.destroyed or part.position == nil then return nil end
                return part.position
            end
        end
    end
    return object.position
end

return {
    engine_handlers = {
        on_added = function()
            if self.type ~= "screamer" then return end
            local launcher = self.launcher
            if launcher == nil or not launcher.is_player then return end
            if vector.dot(self.velocity - launcher.velocity, self.orientation.down) > JETTISON_PUSH then return end
            local aimed = launcher.target
            if aimed == nil or aimed.object == launcher or not aimable(aimed.object) then return end
            target = { object = aimed.object, component = aimed.component }
            self.target = target
            local record = records.missiles.screamer
            speed = record.speed
            turn_rate = record.turn_rate
            homing = speed > 0
        end,

        on_step = function()
            if not homing then return end
            steps += 1
            if steps <= POD_LAUNCH_STEPS then return end
            local object = target.object
            local aim = if aimable(object) then aimedAt(object, target.component) else nil
            if aim == nil then
                homing = false
                return
            end
            local from = self.position
            -- Led along the target's nose by how far it flies in the missile's time to it
            -- (src/engine/game/ai.zig, `intercept`).
            aim += object.orientation.forward * (vector.magnitude(aim - from) / speed * object.speed)
            local orientation = self.orientation
            local off = util.to_local(from, orientation, aim)
            local distance = vector.magnitude(off)
            if distance > LOST_RANGE then
                homing = false
                return
            end
            local pitch_input = 0
            local yaw_input
            if off.z >= 0 then
                pitch_input = math.clamp((-math.atan2(off.y, off.z) - pitch_rate * RATE_DAMPING) * STEER_GAIN, -1, 1)
                yaw_input = math.clamp((math.atan2(off.x, off.z) - yaw_rate * RATE_DAMPING) * STEER_GAIN, -1, 1)
            else
                yaw_input = if off.x < 0 then -1 else 1
            end
            pitch_rate = RATE_INERTIA * pitch_rate + (1 - RATE_INERTIA) * pitch_input * turn_rate
            yaw_rate = RATE_INERTIA * yaw_rate + (1 - RATE_INERTIA) * yaw_input * turn_rate
            local turned = util.turn(util.turn(orientation, "x", pitch_rate), "y", yaw_rate)
            self.orientation = turned
            -- The motor pushes along the nose at full throttle; the AI's push is the throttle's
            -- share, the cosine of the angle off the aim, at least 0.
            local throttle = if distance > 0 then math.max(off.z / distance, 0) else 1
            local held = (1 - INERTIA) / INERTIA * (1 - throttle) * speed
            if held > 0 then self.velocity -= turned.forward * held end
        end,
    },
}
