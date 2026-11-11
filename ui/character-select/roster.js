/**
 * Roster data: the ONLY file you need to edit to add / change a fighter.
 *
 *  id        unique slug. Optional portrait lives at assets/characters/<id>/portrait.png
 *  name      display name            title   one-line epithet
 *  bio       short blurb shown in the preview panel
 *  stats     speed / power / health, each 1-5 (shown as bars AND converted to gameplay modifiers,
 *            see statsToMods() in select.js: 3 = the original dummy numbers)
 *  tint      CSS filter applied to the shared sprite sheet (palette swap). Use "none" for the original.
 *  portrait  optional image path. null = the portrait is cropped from the sprite sheet instead.
 *  special   name of the signature move, shown in the preview panel
 *  sprite    null = the built-in shared sheet (palette-swapped by `tint`). A path such as
 *            "assets/characters/rudepolitic.json" loads that character definition (own sheet, frame timings,
 *            hitboxes and special move; see DEFAULT_CHAR in index.html for the schema). If the file can't be
 *            loaded the fighter is left out of the roster.
 *
 * The politicians are fictional archetypes, not real people.
 */
window.ROSTER = [
  { id: "dummy", name: "Dummy", title: "Muñeco de pruebas",
    bio: "El sparring oficial del gimnasio. Sin trucos ni sorpresas: perfecto para aprender los controles.",
    stats: { speed: 3, power: 3, health: 3 }, tint: "none", portrait: null, sprite: null, special: "Ley de Vivienda" },

  { id: "ministra", name: "La Ministra", title: "Veloz como una enmienda",
    bio: "Esquiva preguntas y puñetazos por igual. Pega poco, pero nunca la pillas en el mismo sitio.",
    stats: { speed: 5, power: 2, health: 3 }, tint: "hue-rotate(300deg) saturate(1.4)", portrait: null, sprite: null, special: "Ley de Vivienda" },

  { id: "portavoz", name: "El Portavoz", title: "Aguanta cualquier rueda de prensa",
    bio: "Lento pero imperturbable. Encaja golpes como quien oye críticas: sin inmutarse.",
    stats: { speed: 2, power: 3, health: 5 }, tint: "hue-rotate(150deg) saturate(1.3)", portrait: null, sprite: null, special: "Ley de Vivienda" },

  { id: "presidente", name: "El Presidente", title: "Mayoría absoluta de puñetazos",
    bio: "Cada golpe es un decreto. Devastador, aunque una sola moción de censura puede tumbarlo.",
    stats: { speed: 3, power: 5, health: 2 }, tint: "sepia(.7) hue-rotate(-20deg) saturate(2.2)", portrait: null, sprite: null, special: "Ley de Vivienda" },

  { id: "rudepolitic", name: "Rude Politic", title: "Un rodillo con corbata roja",
    bio: "Enorme, peludo y con muy mal despertar. No negocia: aplasta enmiendas, y a quien las defienda, con la bandera en alto.",
    stats: { speed: 2, power: 5, health: 4 }, tint: "none", portrait: null,
    sprite: "assets/characters/rudepolitic.json", special: "Golpe Español" },
];
