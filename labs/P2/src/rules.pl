% -*- coding: utf-8 -*-
% ============================================================================
% P2 · 宠物疾病诊断推理规则（SWI-Prolog）
% 推理范式：Horn 子句逻辑 + SLD 归结 + 封闭世界假设（CWA）
% 对比 P1：OWL 描述逻辑 + Tableau 算法 + 开放世界假设（OWA）
% ============================================================================

% === 动态谓词声明（运行时可 assertz/retract）===
:- dynamic has/2.
:- dynamic has_species/2.

% ============================================================================
% 规则 1：确诊 —— 必要症状全匹配 + 排除症状未命中 + 物种匹配
% ============================================================================
% 语义：病例 Patient 的症状覆盖疾病 Disease 的所有必要症状，
%       且未命中任何排除症状，且物种匹配 → 确诊为 Disease
%
% CWA 关键点：\+ has(Patient, S) 在"未断言该症状"时即为 true
% 对比 P1（OWA）：HermiT 不会因"未断言"就判定"没有"，需要显式排除

diagnose(Patient, Disease) :-
    disease(Disease, _, Species),
    species_match(Patient, Species),
    findall(S, necessary(Disease, S), All),
    length(All, N),
    N > 0,
    forall(necessary(Disease, S), has(Patient, S)),
    \+ (nos(Disease, S), has(Patient, S)).

% ============================================================================
% 规则 2：疑似 —— 部分必要症状匹配 + 排除症状未命中
% ============================================================================
% 语义：病例 Patient 匹配部分必要症状（置信度 = 匹配数 / 总数），
%       且未命中任何排除症状 → 疑似 Disease
%
% Prolog 独有：findall + length + 算术计算，OWL/SWRL 无法表达

suspect(Patient, Disease, Confidence) :-
    disease(Disease, _, Species),
    species_match(Patient, Species),
    findall(S, (necessary(Disease, S), has(Patient, S)), Matched),
    findall(S, necessary(Disease, S), All),
    length(Matched, M),
    length(All, N),
    N > 0,
    Confidence is M / N,
    Confidence > 0,
    \+ (nos(Disease, S), has(Patient, S)).

% ============================================================================
% 规则 3：排除 —— 命中排除症状
% ============================================================================
% 语义：病例 Patient 命中疾病 Disease 的某个排除症状 → 排除 Disease

excluded(Patient, Disease) :-
    disease(Disease, _, _),
    nos(Disease, S),
    has(Patient, S).

% ============================================================================
% 规则 4：物种匹配（辅助过滤）
% ============================================================================
% 病例的物种与疾病物种一致时匹配。
% has_species/2 由 reasoner.py 在运行时断言。

species_match(Patient, Species) :-
    has_species(Patient, Species).
species_match(_, Species) :-
    Species = pet.

% ============================================================================
% 规则 5：递归传播链（Prolog 独有能力，OWL/SWRL 无法表达）
% ============================================================================
% 演示：某些疾病之间存在传播关系，Prolog 可递归推理传播链路
% OWL 的 TransitiveProperty 可以做传递闭包，但无法做条件递归

can_transmit(D1, D2) :- transmit_to(D1, D2).
can_transmit(D1, D3) :- transmit_to(D1, D2), can_transmit(D2, D3).

% ============================================================================
% 规则 6：推理链解释（生成可追溯的诊断依据）
% ============================================================================

explain(Patient, Disease, Explanation) :-
    disease(Disease, DiseaseName, _),
    findall(S, (necessary(Disease, S), has(Patient, S)), Matched),
    findall(S, (necessary(Disease, S), \+ has(Patient, S)), Missing),
    findall(S, (nos(Disease, S), has(Patient, S)), Excluded),
    Explanation = explanation{
        disease: DiseaseName,
        matched: Matched,
        missing: Missing,
        excluded: Excluded
    }.
