from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = PROJECT_ROOT / "数据" / "活动信息_人工"


REPAIRS = {
    46: {
        "research_method": "人工查看 Dark War Survival Fandom 的 Events 总页、darkwar.wiki 的 Events & Quests 分类，以及 Survivor Trials、Glory War、Industrial Age、Season Event Calendar 等代表性页面，按活动机制整理。",
        "coverage_notes": "Dark War:Survival 的公开资料比较分散，没有像休闲三消那样完整统一的官方活动目录。本轮主要确认了成长试炼、联盟战、据点争夺、Boss/PvE、派遣与赛季日历这些可重复出现的活动框架；Mutant Mines、Mines Melee、Undersea Market 等更像具体赛季或具体主题节点，先作为代表名称保留，不额外扩写。",
        "source_pages": {
            "Dark War survival Wiki - Events": "Fandom 总览页，适合确认高频事件名称与大类入口。",
            "Dark War Survival Wiki - Events & Quests": "独立 wiki 的活动分类页，能补齐 Fandom 没有覆盖到的事件与任务体系。",
            "Dark War Survival Wiki - Survivor Trials Event Guide": "用于确认 Survivor Trials 的周期、阶段目标和成长引导定位。",
            "Dark War Survival Wiki - Glory War Event Guide": "用于确认 Glory War 的联盟对抗、地图争夺和阶段奖励结构。",
            "Dark War Survival Wiki - Industrial Age Event Guide": "用于确认 Industrial Age 的成长线、阶段目标和赛季化包装。",
            "Dark War Survival Wiki - Season 1 Event Calendar": "用于确认该游戏存在按赛季编排的事件日历，而不只是单点活动。",
        },
        "activity_types": {
            "survivor_trials": {
                "display_name": "Survivor Trials / 生还者试炼",
                "description": "偏新手成长向的阶段活动，通常围绕资源采集、建筑成长、战力提升和指定任务推进展开，属于比较典型的开服或前期引导型活动。",
                "market_research_notes": "更像 early-game onboarding event，用来把新玩家拉进稳定的日常任务与资源循环。",
            },
            "alliance_war_event": {
                "display_name": "Glory War / 联盟战争",
                "description": "以联盟对抗为核心，强调成员协作、集结、领地推进和阶段结算，是典型的中后期公会战玩法。",
                "market_research_notes": "属于标准 SLG 联盟 PvP 主活动，重在组织协作而不是个人单刷。",
            },
            "capital_control": {
                "display_name": "Capital Clash / 首都争夺",
                "description": "围绕核心据点或首都控制权展开，通常包含占领、驻防、争夺时间点和联盟排名奖励。",
                "market_research_notes": "这是很多 SLG 都会有的地图中心目标争夺活动，适合作为赛季或大周期冲突节点。",
            },
            "territory_battle": {
                "display_name": "Territory Triumph / 领地争夺",
                "description": "强调地图地块、联盟领土和推进节奏，玩家通常通过占点、协防和阶段胜负来获得奖励。",
                "market_research_notes": "和 Glory War 类似，但更偏领地推进与地图控制。",
            },
            "boss_pve": {
                "display_name": "Tyrant Comes / Boss 讨伐",
                "description": "偏公会或全服协作的 PvE Boss 活动，通常定时开放，玩家通过集火、伤害排名或阶段解锁来拿奖励。",
                "market_research_notes": "适合作为联盟活跃度与伤害输出的协作型 PvE 节点。",
            },
            "collab_pve": {
                "display_name": "Attack on Titan / 联动讨伐",
                "description": "以 IP 联动包装的特别活动，通常会把 Boss、收集和阶段奖励做成限时主题版本。",
                "market_research_notes": "更像内容包装层的联动活动，底层机制往往仍复用既有 PvE/收集框架。",
            },
            "mission_dispatch": {
                "display_name": "Shadow Calls / 派遣任务",
                "description": "偏任务派遣与日常派送系统，玩家通过派出单位、等待完成或多线并行来获得资源与养成材料。",
                "market_research_notes": "属于轻量异步玩法，常用于填充日常留存和资源回收。",
            },
            "resource_spend_ranking": {
                "display_name": "Modification Contest / 改装竞赛",
                "description": "围绕改装、装备或指定材料消耗展开的冲榜活动，常见于 gear、blueprint、强化材料等资源的集中消耗场景。",
                "market_research_notes": "本质是 spend event，用来驱动囤积资源在活动窗口内集中释放。",
            },
            "faction_trial": {
                "display_name": "Faction Trials / 阵营试炼",
                "description": "偏阵营或兵种维度的试炼玩法，常见于 Fighter、Rider、Shooter 之类分支体系，用来强化培养路线差异。",
                "market_research_notes": "更像长期养成线上的限时试炼，而不是单次大型赛季活动。",
            },
            "season_progression": {
                "display_name": "Season Event Calendar / 赛季活动日历",
                "description": "不是单一玩法，而是把多个阶段活动按赛季顺序排布出来，帮助玩家理解一整轮事件节奏。",
                "market_research_notes": "这类日历说明产品已经有相对稳定的赛季运营框架。",
            },
            "industrial_progression": {
                "display_name": "Industrial Age / 工业时代",
                "description": "偏长期成长和阶段推进的系统化活动，通常会把工业等级、部件、解锁项和阶段奖励打包到同一条成长线上。",
                "market_research_notes": "介于新系统上线和赛季成长线之间，既承担内容更新也承担回流刺激。",
            },
        },
    },
    47: {
        "research_method": "人工查看 Toy Blast Help Center 的 Events 分区和相关 FAQ，重点核对 Toy Pass、Cart Race、Cube Party、Stats 等页面，并用 AppsHunter 的 App Store 事件流补充近期活动包装，按稳定活动机制归类。",
        "coverage_notes": "Toy Blast 的公开资料不像 Toon Blast 那么完整，官方帮助中心能确认的核心长期系统主要集中在 Toy Pass、Cart Race、Cube Party、团队玩法、锦标赛与后期联赛。其余像 Treasure Island、Hoop Shot、Knight's Journey、Toy Coupon、Coin Rush 更像阶段性包装或任务板/促销层，所以本轮按机制并拢，没有把每一次命名变化拆成独立玩法。",
        "source_pages": {
            "Toy Blast Help Center - Events": "官方帮助中心的活动入口，可确认目前可见的活动名和活动分区。",
            "Toy Blast Help Center - What is Toy Pass?": "用于确认通行证结构、奖励轨和高级奖励逻辑。",
            "Toy Blast Help Center - What is Cart Race?": "用于确认竞速型排行活动的目标、结算和参与方式。",
            "Toy Blast Help Center - What is Cube Party?": "用于确认收集步进型活动的推进方式和奖励节点。",
            "Toy Blast Help Center - What are the Stats?": "用于确认游戏内统计页与 Star Tournament、Legends Arena 等后期排行体系之间的关系。",
            "AppsHunter - Toy Pass": "用于补充近期 App Store 事件流里出现的活动包装和命名。",
        },
        "activity_types": {
            "battle_pass": {
                "display_name": "Toy Pass / 通行证",
                "description": "典型 battle pass 结构，围绕阶段任务、奖励轨、免费层与高级层展开，是 Toy Blast 比较明确的长期商业化活动框架。",
                "market_research_notes": "这类活动更偏稳定留存与付费转化，不是短期爆发型活动。",
            },
            "step_collection_event": {
                "display_name": "Cube Party / Rotor Party / 收集步进活动",
                "description": "玩家通过关卡内收集指定物件或累计步骤推进奖励条，属于比较经典的 collection progression event。",
                "market_research_notes": "这是休闲三消里很常见的 evergreen 活动模板，低理解成本、易做换皮。",
            },
            "prelevel_booster_event": {
                "display_name": "Crown Rush / 开局增益冲刺",
                "description": "更偏短周期增益活动，通常要求玩家保持连胜或快速通关，以获得开局 booster、额外奖励或更高分数。",
                "market_research_notes": "这类活动常用来提高短期开局体验，带动连续游玩。",
            },
            "race_competition": {
                "display_name": "Cart Race / 竞速排行",
                "description": "玩家通过持续过关推动自己的进度条，与其他玩家实时比速度或累计成绩，属于经典 race competition。",
                "market_research_notes": "适合做轻量 PvP 氛围，不需要真正实时对战。",
            },
            "pvp_duel": {
                "display_name": "Puzzle Duel / 1v1 对战",
                "description": "强调玩家间直接对抗或镜像竞赛，通常以 1v1 形式比较关卡表现、得分或通关速度。",
                "market_research_notes": "比普通 leaderboard 更强调对手感和对局感，是更强的 PvP 包装。",
            },
            "star_tournament": {
                "display_name": "Star Tournament / 星星锦标赛",
                "description": "围绕星星累计、event wins 或高阶玩家数据展开的锦标赛，常见于主线后期用户池。",
                "market_research_notes": "说明产品已经把部分后期玩家从主线推进中抽离出来做专门竞技循环。",
            },
            "streak_challenge": {
                "display_name": "Sky Path / 连胜路径",
                "description": "玩家通过连续首通、连胜或不失败推进奖励路径，通常在中后段设置 grand prize。",
                "market_research_notes": "本质上是 streak challenge，适合刺激高活跃玩家集中游玩。",
            },
            "team_coop": {
                "display_name": "Team Adventure / 团队协作",
                "description": "以团队总进度为核心，成员共同完成任务、累计进度并解锁共享奖励。",
                "market_research_notes": "适合增强队伍黏性，让弱社交产品也有明确的 team-wide progress bar。",
            },
            "team_competition": {
                "display_name": "Team Race / 团队竞速",
                "description": "队伍之间按通关速度或总成绩竞争名次，属于团队版 race event。",
                "market_research_notes": "相比 Team Adventure 更强调队伍间竞争，而不是只做内部协作。",
            },
            "late_game_league": {
                "display_name": "Legends Arena / 高段位联赛",
                "description": "偏后期或高阶玩家池的联赛体系，用来承接主线外的长期竞技留存。",
                "market_research_notes": "这类模式一般只对高进度用户开放，是典型 endgame league 设计。",
            },
            "minigame_event": {
                "display_name": "Treasure Island / 主题小游戏",
                "description": "以 Treasure Island 这类主题包装承载的小游戏或探索活动，通常用来丰富主玩法之外的节奏。",
                "market_research_notes": "更像内容调味层，重要的是视觉主题和奖励包装。",
            },
            "quest_board_event": {
                "display_name": "Hoop Shot / Knight's Journey / 任务板活动",
                "description": "围绕一组任务节点、路线选择或阶段小目标展开，玩家按任务板逐步清空奖励。",
                "market_research_notes": "常用于把多个轻目标串起来，提高短周期留存和完成感。",
            },
            "economy_promo": {
                "display_name": "Toy Coupon / Coin Rush / 经济促销活动",
                "description": "偏资源加成、优惠券、限时兑换或金币加速类活动，核心是刺激货币消耗与短期转化。",
                "market_research_notes": "更多承担 economy promo 角色，而不是独立玩法。",
            },
        },
    },
    48: {
        "research_method": "人工查看 App Store 描述与 AppsHunter 事件流，重点确认 Marble Sort! 的新机制、新障碍和少量活动包装，按公开可验证的功能与活动整理。",
        "coverage_notes": "Marble Sort! 缺少稳定 wiki 和官方活动中心，公开证据主要来自 App Store 与 AppsHunter。整体看它更像持续新增关卡机关的内容型产品，而不是活动矩阵成熟的 LiveOps 产品；Sugar Rush 是少数明确可见的活动包装，其余更多是 Trio Box、Super Hidden Box、Ice Tray 这类机制更新。",
        "source_pages": {
            "App Store - Marble Sort!": "官方商店页，用于确认产品定位、版本更新和可直接验证的系统关键词。",
            "AppsHunter - Marble Sort! App Page": "用于查看该产品近期 App Store 事件和版本更新摘要。",
            "AppsHunter - New mechanic: Trio box!": "用于确认 Trio Box 作为新关卡机制出现。",
            "AppsHunter - New mechanic: Super Hidden Box": "用于确认 Super Hidden Box 作为新障碍或新机关出现。",
            "AppsHunter - New mechanic: Ice Tray!": "用于确认 Ice Tray 机制及其主题化包装。",
            "AppsHunter - New Event: Sugar Rush": "用于确认少量明确可见的活动名 Sugar Rush。",
            "AppsHunter - New mechanic and levels": "用于确认产品持续通过新机关和新关卡做内容更新。",
        },
        "activity_types": {
            "core_level_system": {
                "display_name": "Core Conveyor Sort Levels / 核心分拣关卡",
                "description": "产品主体仍是标准的颜色分拣/盒子分拣关卡，持续通过新关卡与新障碍维持内容更新。",
                "market_research_notes": "这更像关卡内容迭代，而不是成熟的活动矩阵。",
            },
            "trio_box": {
                "display_name": "Trio Box / 三色盒子",
                "description": "新增关卡机关之一，用三色或多段要求提升分拣复杂度，本质上属于新障碍/新机关投放。",
                "market_research_notes": "说明这款产品主要依靠 mechanic refresh 做更新。",
            },
            "super_hidden_box": {
                "display_name": "Super Hidden Box / 隐藏盒子",
                "description": "以隐藏信息或延迟暴露条件为核心的新机关，增加了试错和观察层。",
                "market_research_notes": "依旧偏关卡机制更新，而不是独立运营活动。",
            },
            "ice_tray": {
                "display_name": "Ice Tray / 冰格机关",
                "description": "通过冻结、阻塞或额外解锁条件增加关卡变化，是典型的 puzzle obstacle update。",
                "market_research_notes": "适合作为版本更新的内容卖点，但对 LiveOps 意义有限。",
            },
            "vault_panel": {
                "display_name": "Vault / Color Panel / 机关面板",
                "description": "属于版本中新加入的面板或机关类型，用来改变颜色流转或可操作区域。",
                "market_research_notes": "更像 level system expansion，不像正式活动。",
            },
            "leaderboard_event": {
                "display_name": "Sugar Rush / 排行活动",
                "description": "目前公开可直接确认的活动名之一，更偏短周期 leaderboard event，可能结合 token、奖励条或阶段排名。",
                "market_research_notes": "从公开材料看，这更像少量穿插的 LiveOps 包装，而不是完整活动体系。",
            },
        },
    },
    49: {
        "name": "Bingo Blitz™ - BINGO Games",
        "research_method": "人工查看 BINGO Blitz Wiki 的 Collection Items、Daily Tournament、Slots Blitz、Pets Blitz Slots、Blitzy's Tale 等页面，并参考 AppsHunter 的品牌活动流，按 Bingo 房间收集、锦标赛、Slots 与专属主题活动归类。",
        "coverage_notes": "Bingo Blitz 的公开框架很成熟，核心由房间收集、稀有收集、每日锦标赛、皇冠赛、Slots 子模式、图册/故事收集和特色房间共同组成。AppsHunter 能看到联动、节日和促销节点，但这些更多是对已有系统的主题包装；房间奖励表与收藏推进仍然是它最核心的长期运营骨架。",
        "source_pages": {
            "BINGO Blitz Wiki": "社区 wiki 首页，用于确认长期系统和高频活动入口。",
            "BINGO Blitz Wiki - Collection Items": "用于确认每个房间都带有 collection items 的收集循环。",
            "BINGO Blitz Wiki - Daily Tournament": "用于确认日常锦标赛的规则、轮次和奖励。",
            "BINGO Blitz Wiki - Free Daily Tournament": "用于补充免费日赛版本与普通日赛的差异。",
            "BINGO Blitz Wiki - Slots Blitz": "用于确认 Slots 子模式和其独立房间体系。",
            "BINGO Blitz Wiki - Pets Blitz Slots": "用于确认带 collection items 的 slots 房间变体。",
            "BINGO Blitz Wiki - Blitzy's Tale": "用于确认 album/故事包装类收集活动。",
            "AppsHunter - American Idol in Bingo Blitz": "用于补充品牌联动或主题化 App Store 活动包装。",
            "AppsHunter - Easter Feaster on Bingo Blitz!": "用于补充节日型活动包装。",
            "AppsHunter - Bingo Blitz + Black Friday = Wow!": "用于补充促销节点和品牌化活动包装。",
        },
        "activity_types": {
            "room_collections": {
                "display_name": "Room Collections / 房间收集",
                "description": "Bingo Blitz 的核心循环之一。玩家在不同房间打 bingo、收集 collection items，并逐步完成房间或地区收藏。",
                "market_research_notes": "这是产品最稳定的 metagame 层，收集驱动力非常强。",
            },
            "shadow_card_collection": {
                "display_name": "Shadow Cards / 稀有影子卡",
                "description": "围绕难获得物件或轮廓卡片展开的补全型收集活动，强调反复进房间与补齐收藏。",
                "market_research_notes": "本质上是稀有收集补完玩法，属于房间收集系统的增强版。",
            },
            "daily_tournament": {
                "display_name": "Daily Tournament / 每日锦标赛",
                "description": "按日开启的多轮锦标赛，玩家通过 bingo、积分或指定动作争取日榜奖励，是高频留存活动。",
                "market_research_notes": "这是典型的高频日循环 tournament，用来稳定活跃。",
            },
            "tournament_crown": {
                "display_name": "Tournament Crown / 皇冠赛",
                "description": "与 Daily Tournament 相关的等级化奖励或皇冠晋级体系，强调连胜、累计 crown 和更高层次奖励。",
                "market_research_notes": "更像锦标赛内部的层级强化机制，用于提高重复参与意愿。",
            },
            "slots_mode": {
                "display_name": "Slots Blitz / Slots 子模式",
                "description": "在主 bingo 之外提供 slots 子玩法，拥有独立房间、货币循环和奖励节奏。",
                "market_research_notes": "说明 Bingo Blitz 不只是 bingo 产品，而是把 slots 作为补充留存层。",
            },
            "slots_room_collection": {
                "display_name": "Pets Blitz Slots / Slots 房间收集",
                "description": "把 slots 与 collection items 结合起来，形成房间主题化和收集并行推进的变体。",
                "market_research_notes": "这是 slots 模式向房间收集 metagame 的延伸。",
            },
            "album_collection": {
                "display_name": "Albums / 图册收集",
                "description": "以 Blitzy's Tale 这类 album 形式承载的主题收集活动，强调成套收集、章节推进和叙事包装。",
                "market_research_notes": "和普通房间收集相比，album 更强调主题化展示与阶段完成感。",
            },
            "special_room": {
                "display_name": "Specialty Rooms / 特色房间",
                "description": "围绕特殊规则、特殊奖励或主题机制打造的房间活动，例如 Blackout Lounge 这种差异化房间体验。",
                "market_research_notes": "适合在既有 bingo 框架里制造新鲜感，而无需改底层规则。",
            },
            "branded_live_event": {
                "display_name": "Branded / Seasonal Live Events / 品牌与节日活动",
                "description": "包括联动、节日活动和商业节点活动，通常以 App Store 事件流或主题包装形式出现。",
                "market_research_notes": "这类活动的重要性在于包装和主题，而不是新玩法本身。",
            },
        },
    },
    50: {
        "research_method": "人工查看 App Store 商店页、AppsHunter 事件流，以及 Reservoir Raid 的社区攻略页，重点确认 Tiles Survive! 中可公开验证的联盟战、赛季主题、通行证、主题小游戏、事件商店与派遣系统更新。",
        "coverage_notes": "Tiles Survive! 没有完整官方 wiki，公开信息主要来自 App Store、AppsHunter 和少量社区攻略。可以确认它并不只是简单的关卡或基地成长产品，而是已经具备联盟战、赛季阵营活动、节庆活动、事件商店、通行证和派遣系统更新等多层活动包装；不过不少活动目前只能看到名称和商店/更新文案，因此本轮优先保留可公开验证的框架。",
        "source_pages": {
            "App Store - Tiles Survive!": "官方商店页，用于确认活动关键词、版本记录和事件商店类描述。",
            "AppsHunter - Tiles Survive! App Page": "用于查看近期 App Store 事件流和版本更新摘要。",
            "AppsHunter - Celebrate Christmas Together!": "用于确认圣诞主题活动与装饰奖励。",
            "AppsHunter - Maddie's Protection": "用于确认角色主题 special event 的存在。",
            "AppsHunter - St. Patrick's: Ode to Emerald": "用于确认节日货币与主题活动包装。",
            "AppsHunter - Spring Expedition now live!": "用于确认探索/小游戏向主题活动。",
            "AppsHunter - Labor Fest now live!": "用于确认带 pass、奖杯和事件货币的节庆活动。",
            "Clashiverse - Tiles Survive Reservoir Raid Guide": "用于确认 Reservoir Raid 的联盟对抗结构和玩法定位。",
        },
        "activity_types": {
            "alliance_battle": {
                "display_name": "Reservoir Raid / 联盟争夺战",
                "description": "偏联盟 PvP 的大规模对抗活动，常见要素包括水点/据点争夺、队伍协作、时间窗和联盟排名奖励。",
                "market_research_notes": "这是产品里最明确的联盟战活动，承担中后期组织协作价值。",
            },
            "season_faction_event": {
                "display_name": "Copper Clash / 赛季阵营活动",
                "description": "以赛季名义包装的 faction-based competition，强调阵营对抗、阶段目标和赛季主题。",
                "market_research_notes": "说明游戏不只是零散活动，而是开始有成体系的赛季包装。",
            },
            "tech_event": {
                "display_name": "Infected Conquest / 科技主题活动",
                "description": "围绕科技、感染题材或系统升级展开的活动/版本主题，更偏功能更新与事件包装结合。",
                "market_research_notes": "介于玩法更新和活动包装之间，属于系统事件化表达。",
            },
            "hero_featured_event": {
                "display_name": "Maddie's Protection / 英雄主题活动",
                "description": "围绕指定 SSR 英雄或角色主题展开的 special event，通常会带专属奖励、限定任务或角色曝光。",
                "market_research_notes": "更像 hero spotlight event，用于提升角色价值和抽取/养成意愿。",
            },
            "festival_decoration_event": {
                "display_name": "Christmas Carnival / 节日装饰活动",
                "description": "以圣诞主题为核心，奖励常包含 settlement decoration、头像框、皮肤或节日收藏物。",
                "market_research_notes": "这是常见的 SLG 节庆包装层，重点在视觉主题和限定奖励。",
            },
            "festival_currency_event": {
                "display_name": "St. Patrick's: Ode to Emerald / 节日货币活动",
                "description": "通过节日代币、兑换道具或 Lucky Pinballs 一类机制驱动玩家在活动窗口内集中参与。",
                "market_research_notes": "典型 event currency 玩法，适合和商店、任务、抽奖联动。",
            },
            "theme_minigame_event": {
                "display_name": "Spring Expedition / 主题小游戏活动",
                "description": "以春季探索或小游戏形式承载的主题活动，通常搭配关卡外玩法、皮肤奖励和节日包装。",
                "market_research_notes": "更像内容调味层，用来丰富主循环之外的体验。",
            },
            "festival_pass_event": {
                "display_name": "Labor Fest / Advanced Pass / 节庆通行证",
                "description": "把节庆任务、奖杯制作、事件货币和 Advanced Pass 放在同一套活动框架内，兼顾留存和付费。",
                "market_research_notes": "说明该产品已经把 crafting、currency、pass 做成可复用的复合活动模板。",
            },
            "event_store": {
                "display_name": "Paw-some Puzzle Party / Gourmet Rush / 事件商店",
                "description": "围绕 Game Tokens 或活动积分开启限时商店，玩家通过参与活动换取资源、外观或成长道具。",
                "market_research_notes": "这是比较标准的 token + event store 组合，适合拉动参与深度。",
            },
            "fishing_event": {
                "display_name": "Fishing Event / 钓鱼活动",
                "description": "独立主题小游戏或收集玩法，通常包含专属掉落、限定道具与阶段奖励。",
                "market_research_notes": "从公开描述看，它承担的是玩法变化和活动包装双重角色。",
            },
            "dispatch_quality_of_life_event": {
                "display_name": "Dire Dispatch / Doomsday Express / 派遣系统更新",
                "description": "偏派遣玩法强化或系统更新，强调快速刷新、自动英雄、多队派遣等 QoL 改进，并以活动名形式对外包装。",
                "market_research_notes": "更像 major update 结合系统活动的表达，不是纯独立玩法。",
            },
        },
    },
}


def main() -> None:
    for rank, config in REPAIRS.items():
        path = next(MANUAL_DIR.glob(f"{rank:02d}_*.json"))
        payload = json.loads(path.read_text(encoding="utf-8"))

        if "name" in config:
            payload["name"] = config["name"]
        payload["research_method"] = config["research_method"]
        if "coverage_notes" in config:
            payload["coverage_notes"] = config["coverage_notes"]

        source_notes = config.get("source_pages", {})
        for source in payload.get("source_pages", []):
            title = source.get("title")
            if title in source_notes:
                source["notes"] = source_notes[title]

        activity_updates = config.get("activity_types", {})
        for activity in payload.get("activity_types", []):
            update = activity_updates.get(activity.get("type"))
            if update:
                activity.update(update)

        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated {path.name}")


if __name__ == "__main__":
    main()
