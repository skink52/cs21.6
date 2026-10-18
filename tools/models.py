"""The 1.6 player models as CS2 player models: each 1.6 model's mesh is moved onto CS2's player skeleton so CS2's own
animations, hit boxes, ragdoll and weapon attachments work with it.

usage: python3 tools/models.py <cstrike dir> <CS2 player model template dir> <addon out dir> [preview dir]

  template dir  a CS2 player model decompiled to ModelDoc (Source 2 Viewer): <name>.vmdl, <name>_thirdperson_body.dmx,
                _firstperson_arms.dmx, _firstperson_sleeves.dmx, _tools_preview.dmx. The first-person arms, skeleton,
                hit boxes, ragdoll, attachments and animation graph are kept; the third-person body is replaced.

How the mesh is moved: every 1.6 bone is matched to a CS2 bone (Bip01 L UpperArm -> arm_upper_L ...). Each piece of
the mesh keeps its shape but is turned so its bone points the way the CS2 bone points (the 1.6 T-pose becomes CS2's
A-pose), stretched along the bone to the CS2 bone's length, and put at the CS2 joint. 1.6 models give each vertex one
bone, as here, so joints bend the way they did in 1.6.

Writes models/player/cs16/<class>/<class>.vmdl (+ _body.dmx), models/player/cs16/shared/ (arms, sleeves, preview pose),
materials/models/player/cs16/<class>/*.vmat + png, and preview pictures (bind pose and the template's preview pose).
"""
import os, sys, re, shutil, copy
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldsrc'))
import dmx9
from dmx9 import Element, T_ELEMENT, T_INT, T_FLOAT, T_STRING, T_VEC2, T_VEC3, T_VEC4, ARRAY
from mdl import MDL, quat_mat

CS, TPL, OUT = sys.argv[1:4]
PREVIEW = sys.argv[4] if len(sys.argv) > 4 else None
CLASSES = ['terror', 'leet', 'arctic', 'guerilla', 'urban', 'gsg9', 'sas', 'gign']
MODEL_DIR = 'models/player/cs16'
MAT_DIR = 'materials/models/player/cs16'
GIRTH = 1.12            # CS2 agents are bigger than the 1.6 models: widen everything by this much

# ---------------------------------------------------------------- the template (CS2 skeleton in its bind pose)
tfiles = os.listdir(TPL)
def tfile(suffix): return os.path.join(TPL, next(f for f in tfiles if f.endswith(suffix)))
TPL_VMDL, TPL_BODY = tfile('.vmdl'), tfile('_thirdperson_body.dmx')
body_tpl = dmx9.DMX.load(TPL_BODY)
skel = body_tpl.root['skeleton']
JOINTS = [j.name for j in skel['jointList']]
JIDX = {n: i for i, n in enumerate(JOINTS)}


def joint_world(dm):
    W = {}
    def walk(j, R, t):
        tr = j['transform']; R2 = R @ quat_mat(tr['orientation']); t2 = R @ np.array(tr['position']) + t
        W[j.name] = (R2, t2)
        for c in j['children'] or []:
            if c.type == 'DmeJoint': walk(c, R2, t2)
    for c in dm.root['skeleton']['children']:
        if c.type == 'DmeJoint': walk(c, np.eye(3), np.zeros(3))
    return W
WCS = joint_world(body_tpl)
def J(n): return WCS[n][1]

# ---------------------------------------------------------------- 1.6 bone -> (CS2 bone, the 1.6 bone whose piece transform it uses)
MAP = {}
def side(s, S):
    m = {
        f'Bip01 {S} Clavicle': ('clavicle_' + s, None), f'Bip01 {S} UpperArm': ('arm_upper_' + s, None),
        f'-- {S} shoulder outside': ('arm_upper_' + s, f'Bip01 {S} UpperArm'), f'-- {S} Shoulder inside': ('arm_upper_' + s, f'Bip01 {S} UpperArm'),
        f'-- {S} bicep twist': ('arm_upper_' + s, f'Bip01 {S} UpperArm'),
        f'Bip01 {S} Forearm': ('arm_lower_' + s, None), f'-- {S} Elbow': ('arm_lower_' + s, f'Bip01 {S} Forearm'),
        f'-- {S} Forearm twist': ('arm_lower_' + s, f'Bip01 {S} Forearm'), f'-- {S} forearm twist': ('arm_lower_' + s, f'Bip01 {S} Forearm'),
        f'Bip01 {S} Hand': ('hand_' + s, None), f'-- {S} wrist': ('hand_' + s, f'Bip01 {S} Hand'),
        f'Bip01 {S} Finger0': ('finger_thumb_0_' + s, None), f'Bip01 {S} Finger01': ('finger_thumb_1_' + s, None),
        f'Bip01 {S} Finger1': ('finger_middle_0_' + s, None), f'Bip01 {S} Finger11': ('finger_middle_1_' + s, None),
        f'-- {S} knuckle': ('finger_middle_0_' + s, f'Bip01 {S} Finger1'),
        f'Bip01 {S} Thigh': ('leg_upper_' + s, None), f'Bip01 {S} Calf': ('leg_lower_' + s, None),
        f'-- {S} Knee': ('leg_lower_' + s, f'Bip01 {S} Calf'), f'Bip01 {S} Foot': ('ankle_' + s, None),
        f'-- {S} ankle': ('ankle_' + s, f'Bip01 {S} Foot'), f'-- {S} Ankle': ('ankle_' + s, f'Bip01 {S} Foot'),
        f'Bip01 {S} Toe0': ('ball_' + s, None),
        f'-- {S} butt': ('pelvis', 'Bip01 Pelvis'), f'-- {S} Butt': ('pelvis', 'Bip01 Pelvis'),
    }
    MAP.update(m)
side('L', 'L'); side('R', 'R')
MAP.update({'Bip01': ('pelvis', 'Bip01 Pelvis'), 'Bip01 Pelvis': ('pelvis', None), 'Bip01 Spine': ('spine_0', None),
            'Bip01 Spine1': ('spine_1', None), 'Bip01 Spine2': ('spine_2', None), 'Bip01 Spine3': ('spine_3', None),
            'Bip01 Neck': ('neck_0', None), '-- Neck smooth': ('neck_0', 'Bip01 Neck'), 'Bip01 Head': ('head_0', None),
            'Bone01': ('head_0', 'Bip01 Head'), 'Bomb': ('spine_2', 'Bip01 Spine2')})
# the bone each piece points along (1.6 child -> CS2 child)
SEG16, SEGCS = {}, {}
for s, S in (('L', 'L'), ('R', 'R')):
    for a, b, c, d in [(f'Bip01 {S} Clavicle', f'Bip01 {S} UpperArm', 'clavicle_' + s, 'arm_upper_' + s),
                       (f'Bip01 {S} UpperArm', f'Bip01 {S} Forearm', 'arm_upper_' + s, 'arm_lower_' + s),
                       (f'Bip01 {S} Forearm', f'Bip01 {S} Hand', 'arm_lower_' + s, 'hand_' + s),
                       (f'Bip01 {S} Hand', f'Bip01 {S} Finger1', 'hand_' + s, 'finger_middle_0_' + s),
                       (f'Bip01 {S} Finger0', f'Bip01 {S} Finger01', 'finger_thumb_0_' + s, 'finger_thumb_1_' + s),
                       (f'Bip01 {S} Finger1', f'Bip01 {S} Finger11', 'finger_middle_0_' + s, 'finger_middle_1_' + s),
                       (f'Bip01 {S} Thigh', f'Bip01 {S} Calf', 'leg_upper_' + s, 'leg_lower_' + s),
                       (f'Bip01 {S} Calf', f'Bip01 {S} Foot', 'leg_lower_' + s, 'ankle_' + s),
                       (f'Bip01 {S} Foot', f'Bip01 {S} Toe0', 'ankle_' + s, 'ball_' + s)]:
        SEG16[a] = b; SEGCS[a] = (c, d)
for a, b, c, d in [('Bip01 Spine', 'Bip01 Spine1', 'spine_0', 'spine_1'), ('Bip01 Spine1', 'Bip01 Spine2', 'spine_1', 'spine_2'),
                   ('Bip01 Spine2', 'Bip01 Spine3', 'spine_2', 'spine_3'), ('Bip01 Spine3', 'Bip01 Neck', 'spine_3', 'neck_0'),
                   ('Bip01 Neck', 'Bip01 Head', 'neck_0', 'head_0')]:
    SEG16[a] = b; SEGCS[a] = (c, d)
# terminal pieces turn with their parent piece: fingertips, toes, head
INHERIT = {}
for s in 'LR':
    INHERIT[f'Bip01 {s} Finger01'] = f'Bip01 {s} Finger0'
    INHERIT[f'Bip01 {s} Finger11'] = f'Bip01 {s} Finger1'
    INHERIT[f'Bip01 {s} Toe0'] = f'Bip01 {s} Foot'
INHERIT['Bip01 Head'] = 'Bip01 Neck'

UNKNOWN = set()
G = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)     # 1.6 faces -Y in its reference pose; CS2 faces +X


def arc(a, b):
    """rotation taking unit vector a onto unit vector b by the shortest arc"""
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.9999:
        ax = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0])
        ax /= np.linalg.norm(ax)
        return 2 * np.outer(ax, ax) - np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def frame(p, s):
    """orthonormal frame from a primary and a secondary direction"""
    x = p / np.linalg.norm(p); z = np.cross(x, s); z /= np.linalg.norm(z); y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def piece_transforms(m):
    """per 1.6 bone: (pivot16, pivotCS, R, axis16, along) mapping a reference-pose point to the CS2 bind pose"""
    names = [b['name'] for b in m.bones]
    T16 = {n: G @ m.T[i] for i, n in enumerate(names)}
    out = {}
    # hips: the pelvis piece hangs from the line between the thighs in both skeletons
    hip16 = (T16['Bip01 L Thigh'] + T16['Bip01 R Thigh']) / 2
    hipcs = (J('leg_upper_L') + J('leg_upper_R')) / 2
    out['Bip01 Pelvis'] = (hip16, hipcs, np.eye(3), None, GIRTH)
    order = [n for n in names if n in SEG16] + [n for n in names if n in INHERIT]
    for n in order:
        if n in SEG16:
            c16, (ccs, ccs2) = SEG16[n], SEGCS[n]
            d16 = T16[c16] - T16[n]; dcs = J(ccs2) - J(ccs)
            L16, Lcs = np.linalg.norm(d16), np.linalg.norm(dcs)
            u16, ucs = d16 / L16, dcs / Lcs
            if 'Hand' in n:
                # hands: also line the thumb up, so the palm faces the right way
                s = n.split()[1]
                t16 = T16[f'Bip01 {s} Finger0'] - T16[n]; tcs = J(f'finger_thumb_0_{s}') - J(ccs)
                R = frame(ucs, tcs) @ frame(u16, t16).T
            elif n.startswith('Bip01 Spine') or n == 'Bip01 Neck':
                R = arc(u16, ucs)
            else:
                R = arc(u16, ucs)
            along = float(np.clip(Lcs / L16, 0.6, 1.8))
            out[n] = (T16[n], J(ccs), R, u16, along)
        else:
            p = out[INHERIT[n]]
            out[n] = (T16[n], J(MAP[n][0]), p[2], None, GIRTH)
    for n in names:
        if n in out or n not in MAP: continue
        main = MAP[n][1]
        if main and main in out: out[n] = out[main]
    # bones this table doesn't know: follow the nearest known parent (and say so)
    for i, n in enumerate(names):
        if n in out: continue
        p = m.bones[i]['parent']
        while p >= 0 and names[p] not in out: p = m.bones[p]['parent']
        out[n] = out[names[p]] if p >= 0 else out['Bip01 Pelvis']
        MAP.setdefault(n, (MAP[names[p]][0] if p >= 0 and names[p] in MAP else 'pelvis', None))
        UNKNOWN.add(n)
    return out, names


def move(points, tr):
    p16, pcs, R, axis, along = tr
    x = points - p16
    if axis is not None:
        a = (x @ axis)[:, None] * axis
        x = a * along + (x - a) * GIRTH
    else:
        x = x * along
    return x @ R.T + pcs


# ---------------------------------------------------------------- textures
def write_material(cls, tex_i, m):
    t = m.textures[tex_i]
    base = re.sub(r'[^a-z0-9_]', '_', os.path.splitext(t['name'])[0].lower())
    d = os.path.join(OUT, MAT_DIR, cls); os.makedirs(d, exist_ok=True)
    rgba = m.texture_rgba(tex_i)
    im = Image.fromarray(rgba, 'RGBA')
    im = im.resize((im.width * 2, im.height * 2), Image.BICUBIC)
    im.convert('RGB').save(os.path.join(d, base + '_color.png'))
    lines = ['// CS 1.6 player texture %s (%s)' % (t['name'], cls), 'Layer0', '{', '\tshader "csgo_complex.vfx"',
             '\tTextureColor "%s/%s/%s_color.png"' % (MAT_DIR, cls, base)]
    if t['flags'] & 0x40:
        Image.fromarray(np.repeat(rgba[..., 3:], 3, 2)).resize((im.width, im.height), Image.NEAREST).save(os.path.join(d, base + '_trans.png'))
        lines += ['\tF_ALPHA_TEST 1', '\tTextureTranslucency "%s/%s/%s_trans.png"' % (MAT_DIR, cls, base), '\tg_flAlphaTestReference "0.500"']
    lines += ['\tTextureNormal "materials/default/default_normal.tga"', '\tTextureRoughness "[0.780000 0.780000 0.780000 0.000000]"',
              '\tTextureMetalness "materials/default/default_metal.tga"', '}']
    open(os.path.join(d, base + '.vmat'), 'w', newline='\n').write('\n'.join(lines) + '\n')
    return '%s/%s/%s.vmat' % (MAT_DIR, cls, base), t['w'], t['h']


# ---------------------------------------------------------------- one class
def build(cls):
    m = MDL(os.path.join(CS, 'models/player/%s/%s.mdl' % (cls, cls)))
    tr, names = piece_transforms(m)
    model = m.bodyparts[0]['models'][0]                       # the body (the bomb / defuse pack body part is left out)
    V, N = m.world(model)
    V16 = V @ G.T; N16 = N @ G.T
    newV = np.zeros_like(V16); newN = np.zeros_like(N16); vj = np.zeros(len(V), int)
    for i in range(len(V)):
        bn = names[model['vbone'][i]]
        t = tr.get(bn) or tr['Bip01 Pelvis']
        newV[i] = move(V16[i:i + 1], t)[0]
        vj[i] = JIDX[MAP.get(bn, ('pelvis',))[0]]
    for i in range(len(N)):
        bn = names[model['nbone'][i]]
        t = tr.get(bn) or tr['Bip01 Pelvis']
        n = t[2] @ N16[i]; newN[i] = n / (np.linalg.norm(n) or 1)
    # corners: (vertex, normal, s, t) -> one DMX vertex each (positions keep their own list)
    mats, sets, texs = [], [], []
    corner_key, cpos, cnorm, cuv = {}, [], [], []
    tri_count = 0
    for me in model['meshes']:
        tex = m.skinref[me['skin']] if me['skin'] < len(m.skinref) else me['skin']
        mat, w, h = write_material(cls, tex, m)
        faces = []
        for tri in me['tris']:
            idx = []
            for (vi, ni, s, t) in tri:
                k = (vi, ni, s, t)
                if k not in corner_key:
                    corner_key[k] = len(cpos); cpos.append(vi); cnorm.append(ni); cuv.append((s / w, t / h))
                idx.append(corner_key[k])
            faces.append(idx)
        mats.append(mat); sets.append(faces); tri_count += len(faces); texs.append(m.texture_rgba(tex))
    # winding: CS2 wants the faces counter-clockwise seen from the front (the side the normals point to)
    agree = 0
    for faces in sets:
        for a, b, c in faces:
            p = newV[[cpos[a], cpos[b], cpos[c]]]
            n = newN[[cnorm[a], cnorm[b], cnorm[c]]].sum(0)
            agree += 1 if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) > 0 else -1
    if agree < 0: sets = [[[a, c, b] for a, b, c in faces] for faces in sets]
    # tangents along u
    P = newV[cpos]; UV = np.array(cuv); NN = newN[cnorm]
    tan = np.zeros((len(cpos), 3))
    for faces in sets:
        for f in faces:
            p0, p1, p2 = P[f]; t0, t1, t2 = UV[f]
            e1, e2 = p1 - p0, p2 - p0; d1, d2 = t1 - t0, t2 - t0
            r = d1[0] * d2[1] - d2[0] * d1[1]
            if abs(r) < 1e-12: continue
            tan[f] += (e1 * d2[1] - e2 * d1[1]) / r
    tan -= NN * (tan * NN).sum(1, keepdims=True)
    ln = np.linalg.norm(tan, axis=1); bad = ln < 1e-9
    tan[bad] = np.cross(NN[bad], [0, 0, 1]) + 1e-6; tan /= np.linalg.norm(tan, axis=1, keepdims=True)
    # ---- the DMX: the template's body with our mesh
    dm = dmx9.DMX.load(TPL_BODY)
    mesh = next(e for e in dm.elements if e.type == 'DmeMesh')
    vd = next(e for e in dm.elements if e.type == 'DmeVertexData')
    fs0 = mesh['faceSets'][0]
    nc = len(cpos)
    jc = vd['jointCount']
    vd['position$0'] = [tuple(map(float, newV[cpos[i]])) for i in range(nc)]
    vd['normal$0'] = [tuple(map(float, NN[i])) for i in range(nc)]
    vd['texcoord$0'] = [(float(u), float(1 - v) if vd.get('flipVCoordinates') else float(v)) for u, v in cuv]
    vd['tangent$0'] = [tuple(map(float, tan[i])) + (1.0,) for i in range(nc)]
    wts, ids = [], []
    for i in range(nc):
        wts += [1.0] + [0.0] * (jc - 1); ids += [int(vj[cpos[i]])] + [0] * (jc - 1)
    vd['blendweights$0'] = wts; vd['blendindices$0'] = ids
    seq = list(range(nc))
    for k in ('position$0Indices', 'normal$0Indices', 'texcoord$0Indices', 'tangent$0Indices'): vd[k] = seq
    new_sets = []
    for mat, faces in zip(mats, sets):
        fs = Element('DmeFaceSet', 'faceSet')
        for k, (t, v) in fs0.attrs.items(): fs.attrs[k] = [t, copy.copy(v)]
        me = Element('DmeMaterial', 'material')
        for k, (t, v) in fs0['material'].attrs.items(): me.attrs[k] = [t, v]
        me['mtlName'] = mat.replace('/', '\\')          # (written the way Source 2 Viewer writes it)
        fs['material'] = me
        fl = []
        for f in faces: fl += f + [-1]
        fs['faces'] = fl
        new_sets.append(fs)
    mesh['faceSets'] = new_sets
    mesh.name = 'cs16_%s_body' % cls
    for e in dm.elements:
        if e.type == 'DmeDag' and e['shape'] is mesh: e.name = 'cs16_%s_body' % cls
    d = os.path.join(OUT, MODEL_DIR, cls); os.makedirs(d, exist_ok=True)
    dm.save(os.path.join(d, '%s_body.dmx' % cls))
    # ---- the vmdl: the template's, with our body and the shared first-person arms
    t = open(TPL_VMDL, encoding='utf-8').read()
    def swap(name, path):
        nonlocal t
        t2 = re.sub(r'(name = "%s"\s*\n\s*filename = ")[^"]+(")' % re.escape(name), r'\g<1>%s\g<2>' % path, t)
        assert t2 != t, 'no render mesh named ' + name
        t = t2
    swap('thirdperson_body', '%s/%s/%s_body.dmx' % (MODEL_DIR, cls, cls))
    swap('firstperson_default_gloves_arms', MODEL_DIR + '/shared/firstperson_arms.dmx')
    swap('firstperson_sleeves', MODEL_DIR + '/shared/firstperson_sleeves.dmx')
    t = re.sub(r'(source_filename = ")[^"]*_tools_preview\.dmx(")', r'\g<1>%s/shared/tools_preview.dmx\g<2>' % MODEL_DIR, t)
    open(os.path.join(d, '%s.vmdl' % cls), 'w', encoding='utf-8', newline='\n').write(t)
    return newV[cpos], np.array(cuv), sets, texs, vj[cpos], tri_count, len(mats)


# ---------------------------------------------------------------- checks: pictures of the bind pose and a posed body
def posed_preview():
    tp = dmx9.DMX.load(tfile('_tools_preview.dmx'))
    pose = {}
    for ch in (e for e in tp.elements if e.type == 'DmeChannel'):
        el, at, log = ch['toElement'], ch['toAttribute'], ch['log']
        if el is None or log is None or at not in ('position', 'orientation'): continue
        lay = log['layers'][0]
        if lay['values']: pose.setdefault(el.name, {})[at] = lay['values'][0]
    # posed world transforms with the template's hierarchy
    Wp = {}
    def walk(j, R, tt):
        tr = j['transform']
        p = pose.get(j.name, {}); pos = p.get('position', tr['position']); q = p.get('orientation', tr['orientation'])
        R2 = R @ quat_mat(q); t2 = R @ np.array(pos) + tt
        Wp[j.name] = (R2, t2)
        for c in j['children'] or []:
            if c.type == 'DmeJoint': walk(c, R2, t2)
    for c in skel['children']:
        if c.type == 'DmeJoint': walk(c, np.eye(3), np.zeros(3))
    return Wp


# ---------------------------------------------------------------- run
shared = os.path.join(OUT, MODEL_DIR, 'shared'); os.makedirs(shared, exist_ok=True)
shutil.copy(tfile('_firstperson_arms.dmx'), os.path.join(shared, 'firstperson_arms.dmx'))
shutil.copy(tfile('_firstperson_sleeves.dmx'), os.path.join(shared, 'firstperson_sleeves.dmx'))
shutil.copy(tfile('_tools_preview.dmx'), os.path.join(shared, 'tools_preview.dmx'))
Wp = posed_preview() if PREVIEW else None
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'preview'))
from model_render import render
MARK = np.array([WCS[n][1] for n in WCS if 'TWIST' not in n and 'finger' not in n and n not in ('eye_target', 'wpn', 'wpnPivot', 'root_motion')])
for cls in CLASSES:
    P, UV, sets, texs, cj, ntri, nmat = build(cls)
    print('%-9s %4d vertices, %4d triangles, %d materials' % (cls, len(P), ntri, nmat) + ('; bones following a parent: ' + ', '.join(sorted(UNKNOWN)) if UNKNOWN else ''))
    UNKNOWN.clear()
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        groups = [(np.array(f), t) for f, t in zip(sets, texs)]
        render(P, UV, groups, os.path.join(PREVIEW, 'model_%s_bind.png' % cls), views=('front', 'side', 'back'), H=700, marks=MARK)
        # skinned to the template's preview pose: each vertex follows its joint
        Q = np.zeros_like(P)
        for i, j in enumerate(cj):
            n = JOINTS[j]; Rb, tb = WCS[n]; Rp, tp_ = Wp[n]
            Q[i] = Rp @ (Rb.T @ (P[i] - tb)) + tp_
        render(Q, UV, groups, os.path.join(PREVIEW, 'model_%s_posed.png' % cls), views=('front', 'three', 'side'), H=700)
