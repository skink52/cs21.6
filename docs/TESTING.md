# First CS2 test (mg_cs16 v0.1.0)

Not run in CS2 yet. After building the map: `map mg_cs16` with bots (`bot_quota 10` for one map, `bot_quota 30` for two,
`bot_quota 50` for three). The console shows `[cs16] v0.1.0 ready: de_dust2, de_train, de_nuke` when the script loads,
and `[cs16] script time: ...` once a minute. After changing the script or HUD, reload the map fully (`disconnect`, then `map`).

## Things only CS2 can answer (the script has a setting for each)

1. **Damage numbers.** `DEBUG_DAMAGE: true` prints every hit. An AK-47 body shot at close range on someone without
   armour should take 36, a headshot 144. If headshots take 4x too much (576), CS2 multiplies the returned damage by the
   hit group again: set `CS2_REAPPLIES_HITGROUP: true`.
2. **Two bombs at once.** With two or three maps running, can a second map's bomb be planted while one is already
   planted? If not, the bomb rounds need a scripted bomb (tell me).
3. **Menu clicks.** Does F open the buy menu with a mouse cursor, and do clicks buy? Does hovering a row show the 1.6
   picture and description on the right? If clicks don't work: `MENU_MOUSE: false` (W / S / E / R instead).
   Does CS2's B key open anything (with "Nobody can buy" in the map)?
4. **Radio sounds** ("Go go go", "Terrorists win"): heard by you only, once, not by the whole server.
5. **Player models**: the class menu changes your agent; no errors about models in the console.
6. **cvars**: `sv_jump_impulse`, `sv_accelerate` and the `mp_` settings set by the script take (`sv_jump_impulse` in the
   console should say 268.33).

## Checklist

- [ ] Spawns: everyone lands on their map's spawns (top line says which map); 2 or 3 maps with enough bots.
- [ ] 1.6 HUD: health, armour, timer (hidden after the bomb is planted), money with +/-, ammo with the ammo icon;
      buy zone / C4 / defuser icons; `!hud classic|raised|off`. Shown over CS2's HUD in a sensible place?
- [ ] Buy menu: categories, team-only weapons, prices, "insufficient funds", buy time message after 90 s, rebuy.
      A bought gun has one magazine; primary ammo fills it.
- [ ] Money: +300 kills, round rewards next round, loss bonus.
- [ ] Rounds: elimination, bomb, defuse, time up (CTs win); with several maps the round ends when all are decided and
      CS2's score goes to the side with more maps.
- [ ] Knife: slash 15/20, stab 65, 195 from behind. HE grenade up to ~100. Falls hurt from lower heights than CS2.
- [ ] Sounds: 1.6 guns, knife, grenades, C4 beeps / plant / defuse / explosion.
- [ ] Bots buy and plant.
- [ ] Doors open (train, nuke), ladders climb, crates break when the bomb goes off.
