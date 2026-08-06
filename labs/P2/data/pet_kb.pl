% -*- coding: utf-8 -*-
% ============================================================
% P2 宠物疾病知识库（由 kb_builder.py 从 CSV 自动生成）
% 推理范式：Prolog 规则推理（Horn 子句 + CWA）
% ============================================================

% --- 疾病定义 ---
disease(d001, '猫瘟', cat).
disease(d002, '猫感冒', cat).
disease(d003, '猫肠炎', cat).
disease(d004, '犬细小病毒', dog).
disease(d005, '犬感冒', dog).
disease(d006, '犬冠状病毒', dog).
disease(d007, '猫尿路感染', cat).
disease(d008, '犬尿路感染', dog).
disease(d009, '猫艾滋病', cat).
disease(d010, '犬副流感', dog).

% --- 必要症状 ---
necessary(d001, '发热').
necessary(d001, '呕吐').
necessary(d001, '腹泻').
necessary(d002, '打喷嚏').
necessary(d002, '流鼻涕').
necessary(d003, '腹泻').
necessary(d003, '呕吐').
necessary(d004, '呕吐').
necessary(d004, '腹泻').
necessary(d004, '精神萎靡').
necessary(d005, '打喷嚏').
necessary(d005, '流鼻涕').
necessary(d006, '呕吐').
necessary(d006, '腹泻').
necessary(d007, '尿频').
necessary(d007, '尿急').
necessary(d007, '尿痛').
necessary(d008, '尿频').
necessary(d008, '尿急').
necessary(d009, '发热').
necessary(d009, '淋巴结肿大').
necessary(d010, '咳嗽').
necessary(d010, '打喷嚏').

% --- 排除症状 ---
nos(d001, '咳嗽').
nos(d001, '流鼻涕').
nos(d002, '发热').
nos(d002, '呕吐').
nos(d003, '发热').
nos(d003, '咳嗽').
nos(d004, '咳嗽').
nos(d005, '呕吐').
nos(d005, '腹泻').
nos(d006, '发热').
nos(d007, '腹泻').
nos(d008, '腹泻').
nos(d009, '腹泻').
nos(d010, '腹泻').

% --- 疾病传播关系（演示 Prolog 递归推理）---
transmit_to(d002, d001).  % 猫感冒未治疗可能继发猫瘟
transmit_to(d005, d004).  % 犬感冒未治疗可能继发犬细小
