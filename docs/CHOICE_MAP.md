# Duel of Fates Choice & Ending Map

This spoiler-heavy map documents the playable routes, major choices, conditional branches, combat gates, and all known endings in **Star Wars: Duel of Fates**.

## Legend

| Shape / Color | Meaning |
| --- | --- |
| Gold | Start, setup, or route hub |
| Red | Anakin route |
| Blue | Obi-Wan route |
| Purple | Padme route |
| Green | Hopeful or redemptive ending |
| Black / Crimson | tragic or dark ending |
| Dashed arrows | conditional unlocks |

## Route Constellation

```mermaid
flowchart LR
    Title["Title Screen"]:::hub --> Intro["Name Entry + Destiny Choice"]:::hub

    Intro -->|"Anakin Skywalker"| A0["Anakin Route<br/>rage, prophecy, manipulation"]:::anakin
    Intro -->|"Obi-Wan Kenobi"| O0["Obi-Wan Route<br/>duty, mercy, brotherhood"]:::obiwan
    Intro -->|"Padme Amidala"| P0["Padme Route<br/>truth, survival, rebellion"]:::padme

    A0 --> AEnd["7 Anakin Endings"]:::ending
    O0 --> OEnd["5 Obi-Wan Endings"]:::ending
    P0 --> PEnd["5 Padme Endings"]:::ending

    AEnd --> Final["17 Total Endings"]:::hub
    OEnd --> Final
    PEnd --> Final

    classDef hub fill:#f8d66d,stroke:#7a5b00,color:#1b1600,stroke-width:2px;
    classDef anakin fill:#3b1111,stroke:#ff5a5a,color:#fff3f3,stroke-width:2px;
    classDef obiwan fill:#102f52,stroke:#71c8ff,color:#eef8ff,stroke-width:2px;
    classDef padme fill:#3b1646,stroke:#df87ff,color:#fff4ff,stroke-width:2px;
    classDef ending fill:#14351f,stroke:#72df8a,color:#f3fff5,stroke-width:2px;
```

## Universal Combat Loop

Most lightsaber duels pass through the same combat engine. Story choices before combat can change enemy strength, Force power, stamina pressure, or secret outcomes after victory.

```mermaid
flowchart TD
    C0["Combat Encounter"]:::combat --> C1{"Choose Action"}:::choice

    C1 -->|"Strike"| Strike["Damage enemy<br/>costs stamina<br/>can crit"]:::combat
    C1 -->|"Defend"| Defend["Reduce next hit<br/>recover stamina"]:::combat
    C1 -->|"Force Push"| Push["Spend FP<br/>heavy damage<br/>possible stun"]:::combat
    C1 -->|"Force Heal"| Heal["Spend FP<br/>recover HP"]:::combat
    C1 -->|"Center Yourself"| Center["Recover stamina + FP<br/>chance for clarity"]:::combat
    C1 -.->|"Bacta Patch if owned"| Bacta["Consume Bacta<br/>large heal"]:::item
    C1 -.->|"Emergency Flare if owned"| Flare["Consume Flare<br/>stun opening"]:::item
    C1 -.->|"Thermal Detonator if owned"| Boom["Consume Detonator<br/>burst damage + stun"]:::item

    Strike --> Check{"Enemy defeated?"}:::choice
    Defend --> Enemy["Enemy turn"]:::combat
    Push --> Check
    Heal --> Enemy
    Center --> Enemy
    Bacta --> Enemy
    Flare --> Check
    Boom --> Check

    Check -->|"yes"| Victory["Story victory branch"]:::good
    Check -->|"no"| Enemy
    Enemy --> Alive{"Player alive?"}:::choice
    Alive -->|"yes"| C1
    Alive -->|"no"| Defeat["Story defeat branch"]:::dark

    classDef combat fill:#202733,stroke:#97b7ff,color:#f3f7ff,stroke-width:2px;
    classDef choice fill:#f8d66d,stroke:#7a5b00,color:#1b1600,stroke-width:2px;
    classDef item fill:#513b00,stroke:#ffd76d,color:#fff8dd,stroke-width:2px;
    classDef good fill:#14351f,stroke:#72df8a,color:#f3fff5,stroke-width:2px;
    classDef dark fill:#23080c,stroke:#ff5a76,color:#fff1f4,stroke-width:2px;
```

## Padme Route Map

Padme's route is a political survival thriller: evidence, witnesses, medical preparation, and public truth determine whether Mustafar becomes a private tragedy or the first crack in the Empire.

```mermaid
flowchart TD
    P0["Padme: Coruscant Apartment"]:::padme
    PRecords["Senate Records"]:::padme
    PPrep["Naboo Yacht Preparation"]:::padme
    PLand["Mustafar Landing"]:::padme
    PTruth["The Three of You"]:::padme
    PEscape["Refinery Escape"]:::padme
    PFinal["Final Broadcast"]:::padme

    PRebellion["ENDING: The Rebellion Has a Voice"]:::good
    PLiving["SECRET ENDING: Answerable"]:::good
    PHidden["ENDING: The Hidden Flame"]:::good
    PQueen["ENDING: Queen of Ashes"]:::dark
    PTragedy["ENDING: The Silenced Witness"]:::dark

    P0 -->|"Fly to Mustafar alone<br/>+Padme bond"| PLand
    P0 -->|"Call Bail Organa<br/>gain Rebellion Beacon<br/>bail_network"| PPrep
    P0 -->|"Inspect Palpatine records"| PRecords
    P0 -->|"Invite Obi-Wan openly<br/>+brotherhood<br/>obiwan_openly_invited"| PPrep

    PRecords -->|"Download contingency<br/>gain Sidious Dossier<br/>+3 clarity"| PPrep
    PRecords -->|"Transmit evidence to Bail<br/>Dossier + Beacon<br/>bail_network"| PPrep
    PRecords -->|"Delete access trail<br/>+Padme bond<br/>+1 clarity"| PPrep
    PRecords -->|"Read deeper<br/>Dossier + Clone Override<br/>+4 clarity, damage"| PPrep

    PPrep -->|"Load med-droids<br/>gain Med-Droid Kit"| PLand
    PPrep -->|"Arm public transmitter<br/>gain Public Transmitter<br/>+1 clarity"| PLand
    PPrep -->|"Bring no one else<br/>padme_isolated"| PLand
    PPrep -->|"Prepare droid extraction<br/>gain Droid Escape Plan<br/>memory shard"| PLand

    PLand -->|"Embrace Anakin<br/>+2 Padme bond<br/>padme_embraced_anakin"| PTruth
    PLand -->|"Name the Temple truth<br/>+1 clarity<br/>named_temple_truth"| PTruth
    PLand -.->|"Show Mustafar Contingency<br/>requires Sidious Dossier<br/>+2 clarity, +2 Padme bond"| PTruth
    PLand -->|"Give Japor Snippet<br/>+2 Padme bond<br/>memory shard"| PTruth
    PLand -.->|"Arm Rebellion Beacon<br/>requires Beacon<br/>beacon_armed"| PTruth

    PTruth -->|"Stand between them<br/>if bond at least 7 or dossier heard: choke avoided<br/>else damage"| PEscape
    PTruth -->|"Order Obi-Wan to explain trap<br/>+brotherhood, +clarity"| PEscape
    PTruth -.->|"Broadcast confrontation<br/>requires Transmitter or Beacon<br/>public_broadcast_started"| PEscape
    PTruth -->|"Mention the children<br/>+3 Padme bond<br/>memory shard"| PEscape
    PTruth -.->|"health reaches 0"| PTragedy

    PEscape -->|"Use med-droids<br/>if kit: heal + twins_stabilized<br/>else damage"| PFinal
    PEscape -->|"Open blast doors<br/>duel_slowed<br/>+brotherhood"| PFinal
    PEscape -->|"Route broadcast<br/>proof_broadcast if Dossier or public broadcast exists"| PFinal
    PEscape -->|"Coolant separation<br/>coolant_separation<br/>damage"| PFinal
    PEscape -.->|"health reaches 0"| PTragedy

    PFinal -->|"Expose Palpatine"| PCheck1{"proof_broadcast<br/>and bail_network?"}:::choice
    PCheck1 -->|"yes"| PRebellion
    PCheck1 -->|"no"| PHidden

    PFinal -->|"Save Anakin alive"| PCheck2{"Padme bond at least 8<br/>clarity at least 5<br/>coolant OR duel_slowed?"}:::choice
    PCheck2 -->|"yes"| PLiving
    PCheck2 -->|"no"| PHidden

    PFinal -->|"Disappear with the children"| PHidden
    PFinal -->|"Seize emergency array"| PQueen

    classDef padme fill:#3b1646,stroke:#df87ff,color:#fff4ff,stroke-width:2px;
    classDef choice fill:#f8d66d,stroke:#7a5b00,color:#1b1600,stroke-width:2px;
    classDef good fill:#14351f,stroke:#72df8a,color:#f3fff5,stroke-width:2px;
    classDef dark fill:#23080c,stroke:#ff5a76,color:#fff1f4,stroke-width:2px;
```

## Anakin Route Map

Anakin's route is built around fear, possession, prophecy, and the possibility of discovering that Sidious designed the duel itself.

```mermaid
flowchart TD
    A0["Anakin: Mustafar Control Center"]:::anakin
    ASearch["Search Control Room"]:::anakin
    ASignal["Encrypted Sidious Signal"]:::anakin
    AVision["Force Vision"]:::anakin
    AVault["Separatist Vault / K-4S"]:::anakin
    APadme["Padme Conversation"]:::anakin
    AObi["Obi-Wan Appears"]:::anakin
    ASidious["Sidious Revelation"]:::anakin
    AConfront["Words Before Blades"]:::anakin
    ACross["Secret Crossroads"]:::anakin
    ADuel["Duel: Anakin vs Obi-Wan"]:::anakin
    ACollapse["Mining Platform Collapse"]:::anakin
    AVictory["Obi-Wan Defeated"]:::anakin
    AFall["Defeat: High Ground"]:::anakin

    ADark["ENDING: The Dark Lord Rises"]:::dark
    AFallen["ENDING: Chosen One - Fallen"]:::dark
    ARedemption["ENDING: Redemption"]:::good
    AExile["ENDING: Exile"]:::good
    AHollow["ENDING: The Empty Throne"]:::dark
    AAlliance["ENDING: The Grey Path"]:::good
    ARebellion["SECRET ENDING: The First Rebellion"]:::good

    A0 -->|"Go to Padme"| APadme
    A0 -->|"Search first"| ASearch
    A0 -->|"Slice console"| ASignal
    A0 -->|"Meditate on power"| AVision

    ASearch -->|"Gain Detonator + Bacta"| AVault

    ASignal -->|"Destroy recording<br/>dark shift"| APadme
    ASignal -->|"Pocket recording<br/>Sidious Recording + clarity"| APadme
    ASignal -->|"Transmit to Padme<br/>sent_recording_to_padme"| APadme

    AVision -->|"Embrace mask<br/>saw_vader_mask"| APadme
    AVision -->|"Reject mask<br/>rejected_mask + clarity"| APadme
    AVision -->|"Reach for Padme<br/>+Padme bond + clarity"| APadme

    AVault -->|"Spare K-4S<br/>Droid Transponder<br/>kas_spared"| APadme
    AVault -->|"Reprogram K-4S<br/>Sabotage Spike<br/>kas_reprogrammed"| APadme
    AVault -->|"Destroy K-4S<br/>dark shift"| APadme

    APadme -->|"Power speech<br/>-Padme bond"| AObi
    APadme -->|"Demand Obi-Wan's words<br/>-Padme bond"| AObi
    APadme -->|"Hold her gently<br/>+Padme bond"| AObi
    APadme -->|"Admit fear<br/>+Padme bond + clarity"| AObi

    AObi -->|"Force choke Padme<br/>choked_padme<br/>heavy dark shift"| ASidious
    AObi -->|"Control anger<br/>choked_padme=false"| ASidious
    AObi -->|"Demand explanation<br/>+clarity"| ASidious

    ASidious -->|"Submit to Sidious<br/>obeyed_sidious"| AConfront
    ASidious -->|"Defy Sidious<br/>defied_sidious + clarity"| AConfront
    ASidious -->|"Ask Obi-Wan about plan<br/>+brotherhood + clarity"| AConfront

    AConfront -->|"Empire arrogance"| ADuel
    AConfront -->|"Admit it may be too late<br/>showed_doubt"| ACross
    AConfront -->|"Ignite saber"| ADuel
    AConfront -.->|"Ask for anti-Sidious help<br/>requires clarity at least 4 or defied_sidious<br/>anti_sidious_pact"| ACross
    AConfront -->|"Anti-Sidious attempt fails"| ADuel

    ACross -->|"Drop weapon"| ARedemption
    ACross -->|"Reject redemption"| ADuel
    ACross -->|"Walk away"| AExile
    ACross -.->|"Turn trap back<br/>requires anti_sidious_pact + Padme bond at least 3"| ARebellion
    ACross -->|"Turn trap back without trust"| ADuel

    ADuel -->|"Victory"| ACollapse
    ADuel -->|"Defeat"| AFall

    AFall -->|"Leap: You underestimate my power"| AFallen
    AFall -->|"Yield"| ARedemption

    ACollapse -->|"Drive Obi-Wan toward lava"| AVictory
    ACollapse -->|"Steady Padme's ship"| AVictory
    ACollapse -.->|"Call K-4S<br/>works only if kas_spared"| AVictory
    ACollapse -->|"Let it burn"| AVictory

    AVictory -->|"Kill Obi-Wan"| ADark
    AVictory -->|"Spare Obi-Wan"| AHollow
    AVictory -->|"Offer alliance"| AAlliance
    AVictory -.->|"Broadcast Sidious betrayal<br/>requires clarity at least 5 or Sidious Recording"| ARebellion

    classDef anakin fill:#3b1111,stroke:#ff5a5a,color:#fff3f3,stroke-width:2px;
    classDef good fill:#14351f,stroke:#72df8a,color:#f3fff5,stroke-width:2px;
    classDef dark fill:#23080c,stroke:#ff5a76,color:#fff1f4,stroke-width:2px;
```

## Obi-Wan Route Map

Obi-Wan's route is about whether duty remains humane when history asks for violence.

```mermaid
flowchart TD
    O0["Obi-Wan: Padme's Ship"]:::obiwan
    OEcho["Force Echo / Qui-Gon"]:::obiwan
    OConfront["Confront Anakin"]:::obiwan
    ODuel["Duel: Obi-Wan vs Anakin"]:::obiwan
    OCollapse["Refinery Collapse"]:::obiwan
    OHigh["The High Ground"]:::obiwan

    OCanon["ENDING: Duty Fulfilled"]:::good
    ODefeat["ENDING: Darkness Reigns"]:::dark
    OMiracle["SECRET ENDING: Brothers Reunited"]:::good
    OMercy["ENDING: Mercy Endures"]:::good
    OBroken["SECRET ENDING: The Broken Mask"]:::good

    O0 -->|"Wait and listen<br/>padme_choked + brotherhood"| OEcho
    O0 -->|"Step out immediately<br/>padme_choked=false"| OEcho
    O0 -->|"Search ship<br/>Bacta + Flare + clarity"| OEcho

    OEcho -->|"Listen for Anakin<br/>heard_quigon + clarity + brotherhood"| OConfront
    OEcho -->|"Stabilize Padme<br/>Medpac Beacon<br/>padme_stabilized"| OConfront
    OEcho -->|"Warn Bail<br/>bail_warned + clarity"| OConfront
    OEcho -->|"Seal heart<br/>-brotherhood"| OConfront

    OConfront -->|"Accuse anger<br/>-brotherhood"| ODuel
    OConfront -->|"I failed you<br/>+brotherhood"| ODuel
    OConfront -->|"There is still good<br/>appealed_to_good"| ODuel
    OConfront -.->|"Expose Sidious trap<br/>requires clarity at least 2<br/>exposed_sidious_trap + appealed_to_good"| ODuel
    OConfront -->|"Cannot prove trap"| ODuel

    ODuel -->|"Victory"| OCollapse
    ODuel -->|"Defeat"| ODefeat

    OCollapse -->|"Pursue Anakin"| OHigh
    OCollapse -.->|"Use Emergency Flare<br/>requires flare<br/>padme_rescue_marked"| OHigh
    OCollapse -->|"Send Bail proof<br/>bail_warned"| OHigh
    OCollapse -->|"Call Anakin through Force<br/>force_called_anakin + brotherhood"| OHigh

    OHigh -->|"Don't try it"| OCanon
    OHigh -->|"Throw saber aside + plead"| OPlead{"appealed_to_good?"}:::choice
    OPlead -->|"yes"| OMiracle
    OPlead -->|"no but survive"| OCanon
    OPlead -->|"no and die"| ODefeat

    OHigh -->|"Force push from edge"| OPush{"Enough Force Power?"}:::choice
    OPush -->|"yes"| OMercy
    OPush -->|"no"| OCanon

    OHigh -.->|"Show Sidious trap<br/>requires exposed trap or Bail warned"| OTrap{"brotherhood at least 7<br/>and force_called_anakin or heard_quigon?"}:::choice
    OTrap -->|"yes"| OBroken
    OTrap -->|"no"| OCanon

    classDef obiwan fill:#102f52,stroke:#71c8ff,color:#eef8ff,stroke-width:2px;
    classDef choice fill:#f8d66d,stroke:#7a5b00,color:#1b1600,stroke-width:2px;
    classDef good fill:#14351f,stroke:#72df8a,color:#f3fff5,stroke-width:2px;
    classDef dark fill:#23080c,stroke:#ff5a76,color:#fff1f4,stroke-width:2px;
```

## Ending Gallery

| Route | Ending | Primary Unlock |
| --- | --- | --- |
| Padme | The Rebellion Has a Voice | Final Broadcast: expose Palpatine with `proof_broadcast` and `bail_network` |
| Padme | Answerable | Save Anakin with `Padme bond >= 8`, `clarity >= 5`, and `coolant_separation` or `duel_slowed` |
| Padme | The Hidden Flame | Disappear with children, or fail the proof/save-Anakin requirements |
| Padme | Queen of Ashes | Seize the Separatist emergency array |
| Padme | The Silenced Witness | Padme reaches 0 HP before the final broadcast |
| Anakin | The Dark Lord Rises | Defeat Obi-Wan, then kill him |
| Anakin | Chosen One - Fallen | Lose the duel, then leap at Obi-Wan |
| Anakin | Redemption | Drop weapon at Crossroads, yield after defeat, or choose the light |
| Anakin | Exile | Crossroads: walk away from Mustafar |
| Anakin | The Empty Throne | Defeat Obi-Wan, then spare him without true redemption |
| Anakin | The Grey Path | Defeat Obi-Wan, then offer alliance |
| Anakin | The First Rebellion | Turn the trap back with enough trust, or broadcast Sidious's betrayal after victory |
| Obi-Wan | Duty Fulfilled | High Ground: warn Anakin, or fail secret mercy/trap conditions but survive |
| Obi-Wan | Darkness Reigns | Lose combat, or plead without enough trust and die |
| Obi-Wan | Brothers Reunited | High Ground: plead after `appealed_to_good` |
| Obi-Wan | Mercy Endures | High Ground: Force push Anakin back with enough Force power |
| Obi-Wan | The Broken Mask | Show Sidious's trap with enough brotherhood and Force-call/Qui-Gon support |

## Secret Condition Index

| Condition | How It Is Usually Built |
| --- | --- |
| `bail_network` | Padme calls Bail, or transmits Senate evidence to Bail |
| `proof_broadcast` | Padme routes the emergency broadcast after obtaining a dossier or starting the public broadcast |
| `anakin_heard_dossier` | Padme shows Anakin the Mustafar Contingency |
| `public_broadcast_started` | Padme broadcasts the confrontation with a Public Transmitter or armed Beacon |
| `duel_slowed` | Padme opens blast doors during the refinery escape |
| `coolant_separation` | Padme triggers coolant floods during the refinery escape |
| `anti_sidious_pact` | Anakin asks Obi-Wan for help after gaining enough clarity or defying Sidious |
| `Sidious Recording` | Anakin pockets the encrypted recording |
| `kas_spared` | Anakin spares K-4S in the Separatist vault |
| `appealed_to_good` | Obi-Wan says there is still good in Anakin, or exposes the Sith trap with enough clarity |
| `exposed_sidious_trap` | Obi-Wan names Sidious's script with `clarity >= 2` |
| `bail_warned` | Obi-Wan sends a coded warning or later proof to Bail |
| `force_called_anakin` | Obi-Wan slows down during the collapse and speaks Anakin's name through the Force |
| `heard_quigon` | Obi-Wan listens for Anakin beneath Vader during the Force Echo |
