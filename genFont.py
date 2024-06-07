import sys
import os
import math
import re
import copy
from functools import reduce

sys.path.append('clsvg')
from clsvg import bezierShape as bs
from clsvg import fasing as fas
from clsvg import svgfile
from stroke import *

threePointCtrl = bs.BezierCtrl.threePointCtrl
pointAndTangent = bs.BezierCtrl.pointAndTangent

GLYPH_ATTRIB = {
    'version': '1.1',
    'x': '0',
    'y': '0',
    'viewBox': '0 0 1024 1024',
    'style': 'enable-background:new 0 0 1024 1024;',
    'xmlns': "http://www.w3.org/2000/svg",
    'space': 'preserve'
    }
TEMP_GLYPH_FILE = 'tempGlyph.svg'
FONT_SIZE = 1024
GLYPFH_WIDTH = 1
CHAR_WIDTH = 1024
FONT_VARSION = "1.0"
DATA_FILE = "./struc_data/struc_data.json"
TEST_GLYPHS_DIR = './test_glyphs'
SYMBOLS_DIR = 'symbols'

def threeTangentsCurver(p1, tangen1, p2, p3, tangen2):
    ctrl = bs.BezierCtrl(p3 - p1, tangen1, tangen2+p3-p1)
    return ctrl.controlInto(bs.BezierCtrl.threePointT(p1, p2, p3), p2-p1)

def ellipticalArc(width, height, x):
    pos = bs.Point(width, height)
    if x:
        p1 = bs.Point(width * bs.SEMICIRCLE, 0)
        p2 = bs.Point(width, height * (1 - bs.SEMICIRCLE))
    else:
        p1 = bs.Point(0, height * bs.SEMICIRCLE)
        p2 = bs.Point(width * (1 - bs.SEMICIRCLE), height)

    return bs.BezierCtrl(pos, p1, p2)

def sinInterpolation(d, t, pos, p1, p2):
    v1 = pos - p1
    unit = (p2 - p1).normalization()
    length = unit.dotProduct(v1)
    tan = math.tan(math.acos(length / v1.distance()))

    targetD = unit * length * d + p1
    targetL = length * d * tan
    return (v1 - unit * length).normalization(targetL * t) + targetD

def angleInterpolation(p1, t1, pos, p2, t2):
    v1 = pos - p1
    bP1 = v1 * t1
    bP2 = v1 + (p2 - pos) * (1 - t2)
    bPos = p2 - p1
    return bs.BezierCtrl(bPos, bP1, bP2)

def extendedInfo(pos, tangent, npath, nctrl, cInfo, strokeWdith):
    p_map = cInfo['p_map']
    view = cInfo['view']

    def mapx(v): return p_map['h'].index(v)
    def mapy(v): return p_map['v'].index(v)
    
    def axis_value(x, y, axis, inverse):
        if axis == 'x':
            if inverse:
                return y
            else:
                return x
        else:
            if inverse:
                return x
            else:
                return y

    def in_view(i, j, axis):
        if axis == 'x':
            return view[i][j]
        else:
            return view[j][i]

    viewX = mapx(pos.x)
    viewY = mapy(pos.y)
    info = {
        'front': [],
        'back': [],
    }

    find_self = False
    for attrs in view[viewY][viewX]:
        if attrs['indexes'][0] == npath and attrs['indexes'][1] == nctrl:
            find_self = True
            continue

        if find_self:
            info['back'].append(attrs)
        else:
            info['front'].append(attrs)

    if tangent.x * tangent.y == 0:
        if tangent.x == 0:
            axis = 'y'
            if tangent.y > 0:
                dirn = 1
            else:
                dirn = -1
        else:
            axis = 'x'
            if tangent.x > 0:
                dirn = 1
            else:
                dirn = -1
        
        axis_list = p_map[axis_value('h', 'v', axis, False)]
        inaxis_list = p_map[axis_value('h', 'v', axis, True)]
        parallel_check = []

        startV1 = axis_value(viewX, viewY, axis, True)
        for advance in range(0, len(inaxis_list)):
            distance = abs(inaxis_list[startV1] - inaxis_list[advance])
            if distance <= max(strokeWdith.x, strokeWdith.y) / 2:
                parallel_check.append(advance)
            elif inaxis_list[advance] > inaxis_list[startV1]:
                break
        
        startV2 = axis_value(viewX, viewY, axis, False)
        j = startV2
        while True:
            for parVal in parallel_check:
                if parVal == startV1 and j == startV2:
                    for attrs in in_view(parVal, j, axis):
                        if [npath, nctrl] == attrs['indexes']:
                            continue
                        if attrs['symbol'] != 'd':
                            if not attrs['padding']:
                                if (attrs['dir'] == '2' or attrs['dir'] == '8') and axis == 'x':
                                    continue
                                elif (attrs['dir'] == '6' or attrs['dir'] == '4') and axis == 'y':
                                    continue
                            info['extend'] = 0
                            break
                    if 'extend' in info:
                        break
                    else:
                        continue
                for attrs in in_view(parVal, j, axis):
                    if attrs['symbol'] != 'd' or not attrs['padding']:
                        if j == startV2:
                            if attrs['padding']:
                                continue
                            elif (attrs['dir'] == '2' or attrs['dir'] == '8') and axis == 'x':
                                continue
                            elif (attrs['dir'] == '6' or attrs['dir'] == '4') and axis == 'y':
                                continue
                        distance = abs(axis_list[startV2] - axis_list[j])
                        info['extend'] = distance
                        break
                if 'extend' in info: break
            if 'extend' in info: break

            j += dirn
            if j < 0 or j == len(axis_list):
                break
        
        j = startV2-dirn
        while j >= 0 and j < len(axis_list):
            for attrs in in_view(startV1, j, axis):
                if (attrs['symbol'] == 'd' and not attrs['padding']) or attrs['indexes'] != [npath, nctrl] or (attrs['indexes'] == [npath, nctrl] and not attrs['padding']):
                    info['areaLen'] = abs(axis_list[startV2] - axis_list[j])
                    j = -2
                    break

            j -= dirn
    else:
        if tangent.y > 0:
            dirnY = 1
        else:
            dirnY = -1
        if tangent.x > 0:
            dirnX = 1
        else:
            dirnX = -1

        info['extend'] = [-1, -1]
        find = [True, True]
        y = viewY
        x = viewX
        while find[0] and find[1]:
            y += dirnY
            x += dirnX
            if y < 0 or y == len(p_map['v']):
                find[0] = False
                y -= dirnY
            if x < 0 or x == len(p_map['h']):
                find[1] = False
                x -= dirnX
                
            if find[0]:
                for i in range(viewY, y+1, dirnY):
                    for attrs in view[i][x]:
                        if attrs['symbol'] != 'd' or not attrs['padding']:
                            distance = abs(p_map['v'][viewY] - p_map['v'][i])
                            info['extend'][1] = distance
                            find[0] = False
                            break
                    if not find[0]: break
            if find[1]:
                for i in range(viewX, x+1, dirnX):
                    for attrs in view[y][i]:
                        if attrs['symbol'] != 'd' or not attrs['padding']:
                            distance = abs(p_map['h'][viewX] - p_map['h'][i])
                            info['extend'][0] = distance
                            find[1] = False
                            break
                    if not find[1]: break
    
    return info

def diagonalInside(p1, p2, npath, nctrl, cInfo):
    p_map = cInfo['p_map']
    view = cInfo['view']

    def mapx(v): return p_map['h'].index(v)
    def mapy(v): return p_map['v'].index(v)
    
    xv = [mapx(p1.x), mapx(p2.x)]
    yv = [mapy(p1.y), mapy(p2.y)]
    xv.sort()
    yv.sort()

    for y in range(yv[0]+1, yv[1]):
        for x in range(xv[0]+1, xv[1]):
            for attrs in view[y][x]:
                if attrs['indexes'] != [npath, nctrl]:
                    return True
    
    find = [
        [
            xv[0], [
                '6',
                '9',
                '3',
            ]
        ],
        [
            xv[1], [
                '4',
                '1',
                '7',
            ]
        ],
    ]
    for i in [0,1]:
        x = find[i][0]
        for y in range(yv[0]+1, yv[1]):
            for attrs in view[y][x]:
                if attrs['padding']:
                    if attrs['symbol'] == 'v':
                        continue
                    return True
                for dir in find[i][1]:
                    if attrs['dir'] == dir and attrs['se'] == i:
                        return True

    find = [
        [
            yv[0], [
                '1',
                '2',
                '3',
            ]
        ],
        [
            yv[1], [
                '7',
                '8',
                '9',
            ]
        ],
    ]
    for i in [0,1]:
        y = find[i][0]
        for x in range(xv[0]+1, xv[1]):
            for attrs in view[y][x]:
                if attrs['padding']:
                    if attrs['symbol'] == 'h':
                        continue
                    return True
                for dir in find[i][1]:
                    if attrs['dir'] == dir and attrs['se'] == i:
                        return True
                    
    return False

def diagonalSplitInfo(p1, p2, npath, nctrl, cInfo):
    p_map = cInfo['p_map']
    view = cInfo['view']

    def mapx(v): return p_map['h'].index(v)
    def mapy(v): return p_map['v'].index(v)
    
    xv = [mapx(p1.x), mapx(p2.x)]
    yv = [mapy(p1.y), mapy(p2.y)]
    xv.sort()
    yv.sort()

    splitY = [p_map['v'][yv[0]]]
    find = [
        [xv[0], '6', 0],
        [xv[1], '4', 1]
    ]
    for i in [0,1]:
        x = find[i][0]
        for y in range(yv[0]+1, yv[1]):
            for attrs in view[y][x]:
                if attrs['symbol'] == 'h':
                    if attrs['padding'] or (attrs['dir'] == find[i][1] and attrs['se'] == find[i][2]):
                        val = p_map['v'][y]
                        if val not in splitY:
                            splitY.append(val)
    splitY.append(p_map['v'][yv[1]])

    splitX = [p_map['h'][xv[0]]]
    find = [
        [yv[0], '2', 0],
        [yv[1], '8', 1]
    ]
    for i in [0,1]:
        y = find[i][0]
        for x in range(xv[0]+1, xv[1]):
            for attrs in view[y][x]:
                if attrs['symbol'] == 'v':
                    if attrs['padding'] or (attrs['dir'] == find[i][1] and attrs['se'] == find[i][2]):
                        val = p_map['h'][x]
                        if val not in splitX:
                            splitX.append(val)
    splitX.append(p_map['h'][xv[1]])

    return [splitX, splitY]

def lineCorrList(cInfo):
    bpaths = cInfo['bpaths']
    unit = cInfo['unit']
    
    corrList = []
    for path in bpaths:
        dirAttrs = fas.strokeDirection(path) + '*'
        notAllowedList = [
            r'.*212.*',
            r'.*232.*',
            r'.*111.*',
            r'.*333.*',
        ]
        for notAllowed in notAllowedList:
            if re.fullmatch(notAllowed, dirAttrs):
                raise Exception('Error stroke: %s' % dirAttrs)

        corrList.append({})
        index = 0
        while index < len(path):
            ctrl = path[index]
            dir = dirAttrs[index]
            if index+1 < len(path):nextCtrl = path[index+1]
            nextDir = dirAttrs[index+1]
            pos = ctrl.pos
            
            corrInfo = {}
            step = 1
            if dir == '1':
                if nextDir == '2':
                    if dirAttrs != '61268*':
                        raise 'undefine'
                    
                    if nextCtrl.pos.y > unit.y*2:
                        raise 'undefine'
                    else:
                        corrInfo['ctrl'] = bs.BezierCtrl(pos+nextCtrl.pos/2)
                        corrList[-1][str(index+1)] = {}
                        corrList[-1][str(index+1)]['ctrl'] = bs.BezierCtrl(nextCtrl.pos/2)
                        corrList[-1][str(index+1)]['corr'] = nextCtrl.pos/2

                    step += 1
                elif nextDir == '4':
                    if not re.fullmatch(r'14\*', dirAttrs):
                        raise 'undefine'
                    corrInfo['ctrl'] = angleInterpolation(bs.Point(), 0.5, pos, pos+nextCtrl.pos, 0.8)
                    corrList[-1][str(index+1)] = 'null'
                    step += 1
                elif nextDir == '1':
                    corrInfo['ctrl'] = threePointCtrl(bs.Point(), pos, pos+nextCtrl.pos)
                    corrList[-1][str(index+1)] = 'null'
                    step += 1
                else:
                    if abs(pos.x) < unit.x * 1.5:
                        corrInfo['ctrl'] = bs.BezierCtrl(pos)
                    elif pos.y < unit.y * 1.5:
                        corrInfo['ctrl'] = bs.BezierCtrl(pos)
                    elif abs(pos.x) < abs(pos.y):
                        p1 = pos / 2
                        p1.x *= abs(p1.x * 0.5 / p1.y)
                        corrInfo['ctrl'] = bs.BezierCtrl(pos, p1=p1)
                    else:
                        p2 = pos / 2.4
                        p2.y += (1 - abs(p2.y * 0.5 / p2.x)) * (pos.y - p2.y)
                        corrInfo['ctrl'] =  bs.BezierCtrl(pos, p2=p2)
            elif dir == '3':
                if nextDir == '2':
                    if nextCtrl.pos.y > unit.y*2:
                        corrInfo['ctrl'] = copy.deepcopy(ctrl)
                        corrInfo['ctrl'].pos.y += unit.y
                        corrInfo['ctrl'].p1 = bs.Point(pos.x, (pos.y + unit.y) * 0.3)

                        corrList[-1][str(index+1)] = {}
                        tempCtrl = copy.deepcopy(nextCtrl)
                        tempCtrl.pos.y -= unit.y
                        corrList[-1][str(index+1)]['ctrl'] = copy.deepcopy(tempCtrl)
                        corrList[-1][str(index+1)]['corr'] = bs.Point(0, unit.y)
                    else:
                        corrInfo['ctrl'] = copy.deepcopy(ctrl)
                        corrInfo['ctrl'].pos.y += nextCtrl.pos.y
                        corrInfo['ctrl'].p1 = bs.Point(pos.x, (pos.y + nextCtrl.pos.y) * 0.3)
                        corrInfo['corr'] = bs.Point(0, -nextCtrl.pos.y)
                        corrList[-1][str(index+1)] = 'null'

                    corrInfo['extend'] = True
                    step += 1
                elif nextDir == '6':
                    corrInfo['ctrl'] = angleInterpolation(bs.Point(), 0.5, bs.Point(pos.x/2, pos.y), bs.Point(pos.x+nextCtrl.pos.x, pos.y), 0.9)
                    corrInfo['extend'] = True
                    corrList[-1][str(index+1)] = 'null'
                    step += 1
                elif nextDir == '3':
                    corrInfo['ctrl'] = threePointCtrl(bs.Point(), pos, pos+nextCtrl.pos)
                    corrList[-1][str(index+1)] = 'null'
                    step += 1
                else:
                    if abs(pos.x) < unit.x * 1.5:
                        corrInfo['ctrl'] = bs.BezierCtrl(pos)
                    elif abs(pos.x) < abs(pos.y):
                        p2 = pos / 2
                        p2.x *= abs(p2.x * 0.5 / p2.y)
                        corrInfo['ctrl'] = bs.BezierCtrl(pos, p2=p2)
                    else:
                        p2 = pos / 2
                        p2.y += pos.y * (1 - abs(p2.y * 0.5 / p2.x)) * 0.5
                        corrInfo['ctrl'] =  bs.BezierCtrl(pos, p2=p2)
            elif dir == '2':
                if nextDir == '1' or nextDir == '3':
                    if pos.y < unit.y * 1.3:
                        corrInfo = 'null'
                        corrList[-1][str(index+1)] = {}
                        corrList[-1][str(index+1)]['ctrl'] = angleInterpolation(bs.Point(), 0.5, bs.Point(0, (pos.y+nextCtrl.pos.y)*0.72), pos+nextCtrl.pos, .8)
                        corrList[-1][str(index+1)]['corr'] = -pos
                    else:
                        tempVal = min(pos.y * 0.5, unit.y*2)
                        corrInfo['ctrl'] = copy.deepcopy(ctrl)
                        corrInfo['ctrl'].pos.y -= tempVal

                        tempCtrl = copy.deepcopy(nextCtrl)
                        tempCtrl.pos.y += tempVal
                        tempCtrl = angleInterpolation(bs.Point(), 1, bs.Point(0, tempCtrl.pos.y * 0.64), tempCtrl.pos, 0.5)
                        corrList[-1][str(index+1)] = {}
                        corrList[-1][str(index+1)]['ctrl'] = copy.deepcopy(tempCtrl)
                        corrList[-1][str(index+1)]['corr'] = bs.Point(0, -tempVal)
                    step += 1
            elif dir == '9':
                corrInfo['ctrl'] = bs.BezierCtrl(pos)
            
            corrList[-1][str(index)] = corrInfo
            index += step

    return corrList

def toStrokes(bpath, cInfo, npath, corrList, char):
    unit = cInfo['unit']
    strokeWidth = getStrokeWidth(unit)
    strokeWidth = bs.Point(strokeWidth['x'], strokeWidth['y'])

    parallelPath = [bs.BezierPath(),  bs.BezierPath()]
    pathList = []
    dirAttrs = fas.strokeDirection(bpath) + '*'

    index = 0
    indexCorr = 0
    while corrList[npath].get(str(index)) == 'null':
        indexCorr += 1
        index += 1
    prePos = bpath.posIn(index) + corrList[npath][str(index)].get('corr', bs.Point())
    preDir = '*'
    while index < len(bpath):
        dir = dirAttrs[index]
        ctrl = corrList[npath][str(index)].get('ctrl', bpath[index])
        currPos = prePos + ctrl.pos

        nectIndex = index+1
        while corrList[npath].get(str(nectIndex)) == 'null':
            nectIndex += 1
        nectDir = dirAttrs[nectIndex]

        if dir == '6':
            pathLen = ctrl.pos.x

            if preDir == '*':
                serif = True
                expInfo = extendedInfo(bpath.posIn(index-indexCorr), -bpath[index].pos, npath, index, cInfo, strokeWidth)
                ctrlCorr = {'corr': bs.Point()}
                for attrs in expInfo['front'] + expInfo['back']:
                    if attrs['symbol'] == 'v':
                        if attrs['padding'] or attrs['dir'] == '2':
                            serif = False
                            continue
                        raise 'undefine'
                    elif attrs['symbol'] == 'd':
                        if attrs['padding']:
                            tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                            tempCtrl = tempCorrInfo['ctrl']
                            tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                            temp = ctrl.intersections(prePos, tempCtrl, tempPos)
                            if len(temp[0]) and ctrl.lengthAt(temp[0][0]) < unit.x:
                                ctrlCorr['corr'] = ctrl.valueAt(temp[0][0])
                                serif = False
                        else:
                            serif = False
                    else:
                        raise 'undefine'
                    
                if serif:
                    STROKE = stroke_6(strokeWidth, 'f')
                    expandLen = expInfo.get('extend', 9999)
                    if expandLen > strokeWidth.x/2:
                        expandLen = strokeWidth.x/2

                    pathLen += expandLen

                    parallelPath[0].start(prePos - bs.Point(expandLen, strokeWidth.y / 2))
                    parallelPath[0].connect(bs.Point(pathLen, 0))
                    parallelPath[1].start(prePos - bs.Point(expandLen, strokeWidth.y / 2))
                    parallelPath[1].connect(bs.Point(STROKE['length'], strokeWidth.y))
                    parallelPath[1].connect(bs.Point(currPos.x - parallelPath[1].endPos().x, 0))
                else:
                    parallelPath[0].start(prePos - bs.Point(0, strokeWidth.y / 2) + ctrlCorr['corr'])
                    parallelPath[0].connect(bs.Point(pathLen-ctrlCorr['corr'].x, 0))
                    parallelPath[1].start(prePos - bs.Point(0, strokeWidth.y / 2) + ctrlCorr['corr'])
                    parallelPath[1].connect(bs.Point(0, strokeWidth.y))
                    parallelPath[1].connect(bs.Point(pathLen-ctrlCorr['corr'].x, 0))
            elif preDir == '2':
                if nectDir != '8':
                    parallelPath[0].connect(currPos+bs.Point(0, -strokeWidth.y/2) - parallelPath[0].endPos())
                    parallelPath[1].connect(currPos+bs.Point(0, strokeWidth.y/2) - parallelPath[1].endPos())
            elif preDir == '1':
                if nectDir != '*':
                    parallelPath[1].connect(parallelPath[0].endPos() - parallelPath[1].endPos())
                    parallelPath[1].append(parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=prePos.y+strokeWidth.y/2, pos=parallelPath[0].posIn(-1))[0])[1].reverse())
                    parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=prePos.y-strokeWidth.y/2, pos=parallelPath[0].posIn(-1))[0])[0]

                    parallelPath[0].connect(currPos+bs.Point(0, -strokeWidth.y/2) - parallelPath[0].endPos())
                    parallelPath[1].connect(currPos+bs.Point(0, strokeWidth.y/2) - parallelPath[1].endPos())
            else:
                raise 'undefine'
            
            if nectDir == '*':
                expInfo = extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, index, cInfo, strokeWidth)
                serif = []
                ctrlCorr = {}
                for attrs in expInfo['front'] + expInfo['back']:
                    if attrs['symbol'] == 'd':
                        tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                        tempCtrl = tempCorrInfo['ctrl']
                        tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])

                        if attrs['padding']:
                            tempPos= tempCtrl.valueAt(tempCtrl.roots(y=currPos.y-16, pos=tempPos)[0], tempPos)
                            if tempPos.x - currPos.x < strokeWidth.x:
                                ctrlCorr['pos'] = tempPos
                                serif.append('d')
                            continue
                        elif attrs['dir'] == '3' and attrs['se'] == 1:
                            ctrlCorr['pos'] = tempCtrl.valueAt(tempCtrl.roots(y=currPos.y-unit.y/2, pos=tempPos)[0], tempPos)
                            serif.append('cd')
                            continue
                        elif attrs['dir'] == '3' and attrs['se'] == 0:
                            if 'v' in serif[0]:
                                continue
                        elif attrs['dir'] == '1' and attrs['se'] == 1:
                            ctrlCorr['pos'] = currPos
                            serif.append('d')
                            continue
                        elif attrs['dir'] == '1' and attrs['se'] == 0:
                            continue
                    elif attrs['symbol'] == 'v':
                        if attrs['padding']:
                            serif.append('v')
                            continue
                        elif attrs['dir'] == '2' and attrs['se'] == 1:
                            serif.append('v')
                            continue
                        elif attrs['dir'] == '2' and attrs['se'] == 0:
                            continue
                    elif attrs['symbol'] == 'h':
                        if attrs['padding']:
                            raise 'undefine'
                        elif attrs['dir'] == '4' and attrs['se'] == 1:
                            continue
                    raise 'undefine'

                if len(serif) == 0:
                    serif = 'yes'
                elif len(serif) == 1:
                    serif = serif[0]
                else:
                    raise 'undefine'

                done = False
                if preDir == '1':
                    if serif == 'cd':
                        tempCtrl = bs.BezierCtrl(ctrlCorr['pos'] - prePos)
                        comp, xcenter = comp_1(strokeWidth, tempCtrl.pos.distance(), 'all')
                        comp = comp.mirror(bs.Point(), bs.Point(0, 10))
                        xcenter = 1 - xcenter
                        comp = bs.controlComp(tempCtrl, comp, prePos, xcenter, fExtend=32)
                        
                        tempCtrl = bs.BezierCtrl(comp.posIn(-1) - comp.startPos())
                        tempT = parallelPath[0][-1].intersections(parallelPath[0].posIn(-1), tempCtrl, comp.startPos())[0]
                        if len(tempT):
                            parallelPath[0][-1] = parallelPath[0][-1].splitting(tempT[0])[0]
                            parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].intersections(parallelPath[1].posIn(-1), tempCtrl, comp.startPos())[0][0])[0]

                            parallelPath[0].connect(comp.posIn(-1) - parallelPath[0].endPos())
                            parallelPath[1].connect(comp.startPos() - parallelPath[1].endPos())
                            parallelPath[1].extend(comp[:-1])
                            done = True
                        else:
                            serif = 'v'
                    if not done:
                        parallelPath[1].connect(parallelPath[0].endPos() - parallelPath[1].endPos())
                        tempPos = parallelPath[0][-1].valueAt(parallelPath[0][-1].roots(y=prePos.y+strokeWidth.y/2, pos=parallelPath[0].posIn(-1))[0], parallelPath[0].posIn(-1))
                        parallelPath[1].connect(tempPos - parallelPath[1].endPos())
                        parallelPath[0][-1] = parallelPath[0][-1].splitting(parallelPath[0][-1].roots(y=prePos.y-strokeWidth.y/2, pos=parallelPath[0].posIn(-1))[0])[0]
                        
                        parallelPath[0].connect(currPos+bs.Point(0, -strokeWidth.y/2) - parallelPath[0].endPos())
                        parallelPath[1].connect(currPos+bs.Point(0, strokeWidth.y/2) - parallelPath[1].endPos())

                if not done:
                    if serif == 'yes':
                        STROKE = stroke_6(strokeWidth, 'b')
                        expandLen = expInfo.get('extend', 9999)/2

                        if expandLen > STROKE['h'][1]:
                            expandLen = STROKE['h'][1]
                        pathLen = parallelPath[1][-1].pos.x + expandLen
                        tempVal = STROKE['h'][0] + STROKE['h'][1]
                        if pathLen < tempVal:
                            if pathLen * 2 < tempVal:
                                raise 'undefine'
                            
                            if pathLen * 2/3 < tempVal:
                                ratio = pathLen * 2/3 / tempVal
                                STROKE['h'][0] *= ratio
                                STROKE['h'][1] *= ratio
                        
                        parallelPath[0][-1].pos.x += expandLen
                        parallelPath[0][-1].pos.x -=  STROKE['h'][0] + STROKE['h'][1]                        
                        parallelPath[0].connect(bs.Point(STROKE['h'][0], -STROKE['v'][0]))
                        parallelPath[0].connect(bs.Point(STROKE['h'][1], STROKE['v'][0] + strokeWidth.y - STROKE['v'][1]))
                        parallelPath[0].append(ellipticalArc(-STROKE['h'][2], STROKE['v'][1], False))
                        parallelPath[1][-1].pos.x += parallelPath[0].endPos().x - parallelPath[1].endPos().x
                    elif serif == 'v':
                        parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                    elif serif == 'd':
                        parallelPath[0][-1].pos.x += ctrlCorr['pos'].x - parallelPath[0].endPos().x
                        parallelPath[1][-1].pos.x += ctrlCorr['pos'].x - parallelPath[1].endPos().x
                        parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                    else:
                        raise 'undefine'
                    
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif nectDir == '2' or nectDir == '1':
                STROKE = stroke_6(strokeWidth, 'below')

                parallelPath[0][-1].pos.x -=  STROKE['h'][0]
                parallelPath[0].connect(bs.Point(STROKE['h'][0], -STROKE['v'][0]))
                
                tempCtrl = pointAndTangent(bs.Point(0,1), bs.Point(), bs.Point(STROKE['h'][1], STROKE['v'][1]), bs.Point(strokeWidth.x/2, sum(STROKE['v'][1:])), .32)
                tempCtrl = tempCtrl.splitting(tempCtrl.extermesXY()[0][0])
                parallelPath[0].extend(tempCtrl)
                parallelPath[1][-1].pos.x -= strokeWidth.x/2
            elif nectDir == '8':
                STROKE = stroke_6(strokeWidth, 'above')

                if parallelPath[0][-1].pos.y <= STROKE['v'][0]:
                    parallelPath[0].popBack()
                else:
                    parallelPath[0][-1].pos.y -= STROKE['v'][0]
                if parallelPath[1][-1].pos.y <= STROKE['v'][0]:
                    parallelPath[1].popBack()
                else:
                    parallelPath[1][-1].pos.y -= STROKE['v'][0]

                tempPos = parallelPath[0].endPos()
                tempCtrl = angleInterpolation(bs.Point(), 1.0, bs.Point(0, currPos.y-tempPos.y-strokeWidth.x/2), bs.Point((ctrl.pos.x-strokeWidth.x)/2, currPos.y-tempPos.y-strokeWidth.x/2), 0.92)
                tempCtrl = tempCtrl.radianSegmentation(math.pi/4)[0]
                parallelPath[0].extend(tempCtrl)
                
                tempPos = parallelPath[1].endPos()
                tempCtrl = angleInterpolation(bs.Point(), 1.0, bs.Point(0, currPos.y-tempPos.y+strokeWidth.x/2), bs.Point((ctrl.pos.x+strokeWidth.x)/2, currPos.y-tempPos.y+strokeWidth.x/2), 0.8)
                tempCtrl = tempCtrl.radianSegmentation(math.pi/4)[0]
                parallelPath[1].extend(tempCtrl)
                
                tempPos = ctrl.pos.x/2 + STROKE['h'][2]
                tempCtrl = bs.BezierCtrl(p1=bs.Point(10,0), p2=bs.Point(tempPos, -10), pos=bs.Point(tempPos, -STROKE['v'][3]))
                tempCtrl, tempT = tempCtrl.threeTangentCurver(bs.Point(-1,1), bs.Point(tempPos-STROKE['h'][3], -STROKE['v'][4]), tVal=True, none=False)
                tempCtrl = tempCtrl.splitting(tempT)
                parallelPath[1].extend(tempCtrl)
            else:
                raise 'undefine'
        elif dir == '2':
            pathLen = ctrl.pos.y

            if preDir == '*':
                serif = []
                request = []
                expInfo = extendedInfo(bpath.posIn(index-indexCorr), -bpath[index].pos, npath, index, cInfo, strokeWidth)
                checkSpace = expInfo['front']+expInfo['back']
                ctrlCorr = {}
                for i in range(len(checkSpace)):
                    attrs = checkSpace[i]
                    if attrs['symbol'] == 'h':
                        if attrs['padding'] or (attrs['dir'] == '6' and attrs['se'] == 1) or (attrs['dir'] == '4' and attrs['se'] == 0):
                            serif.append('h')
                            continue
                        elif (attrs['dir'] == '6' and attrs['se'] == 0) or (attrs['dir'] == '4' and attrs['se'] == 1):
                            serif.append('s6')
                            continue
                        elif 'c1' in serif:
                            continue
                        raise 'undefine'
                    elif attrs['symbol'] == 'v':
                        if not attrs['padding']:
                            if attrs['dir'] == '2':
                                # request.append('h')
                                continue
                        raise 'undefine'
                    elif attrs['symbol'] == 'd':
                        if attrs['padding']:
                            ctrlCorr['dIndexes'] = attrs['indexes']
                            tempCorr = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                            tempCtrl = tempCorr['ctrl']
                            tempPos = cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1]) + tempCorr.get('corr', bs.Point())
                            temp = tempCtrl.roots(x=prePos.x-strokeWidth.x/2, pos=tempPos)
                            if len(temp):
                                temp = tempCtrl.valueAt(temp[0], tempPos)
                                if temp.y > prePos.y:
                                    ctrlCorr['corr'] = bs.Point(0, temp.y - prePos.y)
                                    serif.append('d')

                                    ctrlCorr['tangents'] = tempCtrl.tangents(tempCtrl.roots(x=prePos.x, pos=tempPos)[0], pos=tempPos)
                        elif attrs['dir'] == '1' and attrs['se'] == 0:
                            if 'h' not in serif[0] and 'c1' not in serif[0]:
                                raise 'undefine'
                        elif attrs['dir'] == '1' and attrs['se'] == 1:
                            if 'h' in serif:
                                break

                            tempCorr = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                            tempCtrl = tempCorr['ctrl']
                            tempPos = cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1]) + tempCorr.get('corr', bs.Point())
                            if tempCtrl.pos.x + tempPos.x < prePos.x and tempCtrl.pos.y + tempPos.y >= prePos.y - 1:
                                tempCtrl = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]['ctrl']
                                tempPos = cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                                tempT = tempCtrl.roots(x=prePos.x, pos=tempPos)[0]
                                ctrlCorr['tangents'] = tempCtrl.tangents(tempT, strokeWidth.x/2, tempPos)
                                serif.append('c1')
                            else:
                                ctrlCorr['splitCtrl'] = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]['ctrl'].reverse()
                                serif.append('s1')
                        elif attrs['dir'] == '3' and attrs['se'] == 0:
                            if 'd' in serif:
                                tempCorr = corrList[ctrlCorr['dIndexes'][0]][str(ctrlCorr['dIndexes'][1])]
                                tempCtrl = tempCorr['ctrl']
                                tempPos = cInfo['bpaths'][ctrlCorr['dIndexes'][0]].posIn(ctrlCorr['dIndexes'][1]) + tempCorr.get('corr', bs.Point())
                                tempT = tempCtrl.roots(x=prePos.x, pos=tempPos)[0]
                                ctrlCorr['pos'] = tempCtrl.valueAt(tempT, tempPos) - prePos
                                ctrlCorr['tangents'] = tempCtrl.tangents(tempT, 10, tempPos)
                                serif[serif.index('d')] = 'hd'
                            else:
                                raise 'undefine'
                        else:
                            raise 'undefine'
                    else:
                        raise 'undefine'
                
                for r in request:
                    if r not in serif:
                        raise 'undefine'

                if len(serif) == 0:
                    serif = 'yes'
                elif len(serif) == 1:
                    serif = serif[0]
                else:
                    if 'h' in serif:
                        if 's1' in serif: serif.remove('s1')
                        if 'c1' in serif: serif.remove('h')
                    elif serif == ['c1', 's6']:
                        serif.remove('c1')
                    elif serif == ['s1', 's6']:
                        serif.remove('s6')
                    
                    if len(serif) == 1:
                        serif = serif[0]
                    else:
                        raise 'undefine'

                expandLen = expInfo.get('extend', 9999)
                if serif == 'yes':
                    STROKE = stroke_2(strokeWidth, 'f')
                    if expandLen > STROKE['v'][0]:
                        expandLen = STROKE['v'][0]

                    areaLen = abs(ctrl.pos.y)
                    if nectDir == '*':
                        areaLen /= 2
                    if areaLen+expandLen < sum(STROKE['v']):
                        ratio = (areaLen+expandLen) / sum(STROKE['v'])
                        if ratio < 0.66:
                            raise 'undefine'
                        STROKE['v'] = [v * ratio for v in STROKE['v']]
                    
                    pathLen += expandLen

                    parallelPath[0].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    tempCtrl = pointAndTangent(bs.Point(0,1), bs.Point(), bs.Point(STROKE['h'][0] + strokeWidth.x, STROKE['v'][0]), bs.Point(strokeWidth.x, sum(STROKE['v'])), .33)
                    tempCtrl = tempCtrl.splitting(tempCtrl.extermesXY()[0][0])
                    parallelPath[0].extend(tempCtrl)
                    parallelPath[0].connect(bs.Point(0, pathLen - sum(STROKE['v'])))
                    parallelPath[1].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    parallelPath[1].connect(bs.Point(0, pathLen))
                elif serif == 'd':
                    STROKE = stroke_2(strokeWidth, 'f')
                    if (pathLen - ctrlCorr['corr'].y)/(STROKE['v'][0]+STROKE['v'][1]) > 3:
                        parallelPath[0].start(prePos - bs.Point(strokeWidth.x/2, -ctrlCorr['corr'].y))
                        tempCtrl = pointAndTangent(bs.Point(0,1), bs.Point(), bs.Point(STROKE['h'][0] + strokeWidth.x, STROKE['v'][0]), bs.Point(strokeWidth.x, sum(STROKE['v'])), .33)
                        tempCtrl = tempCtrl.splitting(tempCtrl.extermesXY()[0][0])
                        parallelPath[0].extend(tempCtrl)
                        parallelPath[0].connect(bs.Point(0, pathLen - sum(STROKE['v']) - ctrlCorr['corr'].y))
                        parallelPath[1].start(prePos - bs.Point(strokeWidth.x/2, -ctrlCorr['corr'].y))
                        parallelPath[1].connect(bs.Point(0, pathLen - ctrlCorr['corr'].y))
                    else:
                        tempPos = [bs.Point(prePos.x + strokeWidth.x/2, 0), bs.Point(prePos.x - strokeWidth.x/2, 0)]
                        tempPos.append(bs.intersection(tempPos[0], tempPos[0]+bs.Point(0, 10), ctrlCorr['tangents'][0], ctrlCorr['tangents'][1]))
                        tempPos.append(bs.intersection(tempPos[1], tempPos[1]+bs.Point(0, 10), ctrlCorr['tangents'][0], ctrlCorr['tangents'][1]))
                        
                        parallelPath[0].start(tempPos[3])
                        parallelPath[0].connect(tempPos[2] - tempPos[3])
                        parallelPath[0].connect(currPos - tempPos[2] + bs.Point(strokeWidth.x/2, 0))
                        parallelPath[1].start(tempPos[3])
                        parallelPath[1].connect(currPos - tempPos[3] - bs.Point(strokeWidth.x/2, 0))
                elif serif == 'h':
                    parallelPath[0].start(prePos - bs.Point(strokeWidth.x/2, 0))
                    parallelPath[0].connect(bs.Point(strokeWidth.x, 0))
                    parallelPath[0].connect(bs.Point(0, pathLen))
                    parallelPath[1].start(prePos - bs.Point(strokeWidth.x/2, 0))
                    parallelPath[1].connect(bs.Point(0, pathLen))
                elif serif == 'hd':
                    comp = bs.BezierPath()
                    comp.start(bs.Point(currPos.x-strokeWidth.x/2, currPos.y))
                    comp.connect(bs.Point(0, -currPos.y))
                    comp.connect(bs.Point(strokeWidth.x, 0))
                    comp.connect(bs.Point(0, currPos.y))
                    tempSplit = comp.splitting(ctrlCorr['tangents'][0], ctrlCorr['tangents'][1])[1]

                    parallelPath[0] = tempSplit[1]
                    parallelPath[1].start(tempSplit[1].startPos())
                    parallelPath[1].connect(tempSplit[0].endPos() - tempSplit[1].startPos())
                    parallelPath[1].connectPath(tempSplit[0].reverse())
                elif serif == 's6':
                    STROKE = stroke_2(strokeWidth, 's6')
                    if expandLen < STROKE['v'] / 2:
                        raise 'undefine'
                    else:
                        expandLen = STROKE['v']
                    pathLen += expandLen

                    parallelPath[0].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    parallelPath[0].connect(bs.Point(STROKE['h'], expandLen))
                    parallelPath[0].connect(bs.Point(strokeWidth.x - STROKE['h'], 0))
                    parallelPath[0].connect(bs.Point(0, pathLen - expandLen))
                    parallelPath[1].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    parallelPath[1].connect(bs.Point(0, pathLen))
                elif serif == 's1':
                    STROKE = stroke_2(strokeWidth, 's6')
                    expandLen = STROKE['v']
                    pathLen += expandLen

                    parallelPath[0].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    tempCtrl = bs.BezierCtrl(bs.Point(STROKE['h'], STROKE['v'])*100)
                    tempPos = ctrlCorr['splitCtrl'].valueAt(tempCtrl.intersections(parallelPath[0].startPos(), ctrlCorr['splitCtrl'], prePos)[1][0], prePos)
                    parallelPath[0].connect(tempPos - parallelPath[0].startPos())
                    tempPos = ctrlCorr['splitCtrl'].valueAt(ctrlCorr['splitCtrl'].roots(x=prePos.x+strokeWidth.x/2, pos=prePos)[0], prePos)
                    parallelPath[0].connect(tempPos - parallelPath[0].endPos())
                    parallelPath[0].connect(bs.Point(0, currPos.y - parallelPath[0].endPos().y))

                    parallelPath[1].start(prePos - bs.Point(strokeWidth.x/2, expandLen))
                    parallelPath[1].connect(bs.Point(0, pathLen))
                elif serif == 'c1':
                    parallelPath[0].start(ctrlCorr['tangents'][1])
                    parallelPath[0].connect((ctrlCorr['tangents'][0]-ctrlCorr['tangents'][1])*2)
                    parallelPath[0].connect(bs.Point(0, currPos.y-parallelPath[0].endPos().y))
                    parallelPath[1].start(ctrlCorr['tangents'][1])
                    parallelPath[1].connect(bs.Point(0, currPos.y-parallelPath[1].endPos().y))
                else:
                    raise 'undefine'
            elif preDir == '6' or preDir == '1' or preDir == '9' or preDir == '3':
                parallelPath[0].connect(bs.Point(0, currPos.y - parallelPath[0].endPos().y))
                parallelPath[1].connect(bs.Point(0, currPos.y - parallelPath[1].endPos().y))
            else:
                raise 'undefine'
            
            if nectDir == '*':
                expInfo = extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, index, cInfo, strokeWidth)
                serif = []
                request = []
                ctrlCorr = {}
                for attrs in expInfo['front'] + expInfo['back']:
                    if attrs['symbol'] == 'h':
                        if attrs['padding']:
                            serif.append('h')
                            continue
                        elif attrs['dir'] == '6':
                            if 'd' not in serif:
                                serif.append('e6')
                            continue
                        elif attrs['dir'] == '4' and attrs['se'] == 1:
                            continue
                    elif attrs['symbol'] == 'v':
                        if not attrs['padding']:
                            if attrs['dir'] == '2':
                                # if 'h' in serif:
                                    continue
                    elif attrs['symbol'] == 'd':
                        if attrs['padding']:
                            tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                            tempCtrl = tempCorrInfo['ctrl']
                            tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])

                            tempT = tempCtrl.roots(x=prePos.x, pos=tempPos)[0]
                            ctrlCorr['tangents'] = tempCtrl.tangents(tempT, 10, tempPos)
                            serif.append('d')
                            continue
                        elif attrs['dir'] == '3' and attrs['se'] == 0:
                            request.append('h')
                            continue
                        elif attrs['dir'] == '3' and attrs['se'] == 1:
                            tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                            if 'extend' in tempCorrInfo:
                                tempCtrl = tempCorrInfo['ctrl']
                                tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                                tempT = tempCtrl.roots(x=prePos.x, pos=tempPos)[0]
                                ctrlCorr['tangents'] = tempCtrl.tangents(tempT, 10, tempPos)
                                serif.append('d')
                                continue
                            raise 'undefine'
                        elif attrs['dir'] == '1':
                            # request.append('h')
                            continue
                    raise 'undefine'

                for r in request:
                    if r not in serif:
                        raise 'undefine'

                if len(serif) == 0:
                    serif = 'yes'
                elif len(serif) == 1:
                    serif = serif[0]
                else:
                    raise 'undefine'

                expandLen = expInfo.get('extend', 9999)
                if serif == 'yes':
                    STROKE = stroke_2(strokeWidth, 'b')
                    if expandLen < STROKE['length']:
                        parallelPath[0][-1].pos.y -= STROKE['length'] - expandLen
                    else:
                        expandLen = STROKE['length']

                    parallelPath[0].append(ellipticalArc(-strokeWidth.x, STROKE['length'], False))
                    parallelPath[1][-1].pos.y += expandLen
                elif serif == 'e6':
                    STROKE = stroke_2(strokeWidth, 'e6')
                    if expandLen > sum(STROKE['v'])/2:
                        if expandLen < sum(STROKE['v']):
                            STROKE['v'][0] /= 2
                            STROKE['v'][1] /= 2
                        expandLen = sum(STROKE['v'])
                        
                        parallelPath[0][-1].pos.y += STROKE['v'][0]
                        parallelPath[0].append(ellipticalArc(-strokeWidth.x, STROKE['v'][1], False))
                        parallelPath[1][-1].pos.y += expandLen
                    else:
                        parallelPath[1][-1].pos.y += expandLen
                        parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                elif serif == 'h':
                    parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                elif serif == 'd':
                    tempPos = bs.intersection(ctrlCorr['tangents'][0], ctrlCorr['tangents'][1], parallelPath[0].posIn(-1), parallelPath[0].endPos())
                    parallelPath[0][-1] = bs.BezierCtrl(tempPos - parallelPath[0].posIn(-1))
                    tempPos = bs.intersection(ctrlCorr['tangents'][0], ctrlCorr['tangents'][1], parallelPath[1].posIn(-1), parallelPath[1].endPos())
                    parallelPath[1][-1] = bs.BezierCtrl(tempPos - parallelPath[1].posIn(-1))
                    parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                else:
                    raise 'undefine'
                    
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif nectDir == '6' and not re.fullmatch(r'268\*', dirAttrs[index:]):
                expInfo = extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, index, cInfo, strokeWidth)
                STROKE = stroke_2(strokeWidth, 'e6')
                expandLen = expInfo.get('extend', 9999)
                if expandLen < sum(STROKE['v']):
                    raise 'undefine'
                else:
                    expandLen = sum(STROKE['v'])

                parallelPath[0][-1].pos.y -= strokeWidth.y / 2
                parallelPath[1][-1].pos.y += STROKE['v'][0]
                parallelPath[1].append(ellipticalArc(strokeWidth.x, STROKE['v'][1], False))
                parallelPath[1].connect(bs.Point(0, strokeWidth.y/2 - expandLen))
            elif nectDir == '1' or nectDir == '3' or nectDir == '4' or nectDir == '6' or nectDir == '9':
                pass # Nothing
            else:
                raise 'undefine'
        elif dir == '3':
            expInfo = [
                extendedInfo(bpath.posIn(index-indexCorr), -bpath[index].pos, npath, index-indexCorr, cInfo, strokeWidth),
                extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, nectIndex-1, cInfo, strokeWidth)
            ]
            serif = [[],[]]
            ctrlCorr = {}
            ctrlCorr2 = {}
            
            def check(f, b):
                if f:
                    request = []
                    for attrs in expInfo[0]['front']+expInfo[0]['back']:
                        # if attrs['indexes'] == [npath, index-indexCorr]: continue
                        if attrs['symbol'] == 'h':
                            if attrs['padding']:
                                serif[0].append('h')
                                continue
                            elif attrs['dir'] == '6' and attrs['se'] == 0:
                                if 'd' in serif[0]:
                                    continue
                            elif attrs['dir'] == '6' and attrs['se'] == 1:
                                request.append('v')
                                continue
                        elif attrs['symbol'] == 'v':
                            if attrs['padding']:
                                serif[0].append('v')
                                continue
                            elif attrs['dir'] == '2' and attrs['se'] == 0:
                                continue
                            elif attrs['dir'] == '2' and attrs['se'] == 1:
                                continue
                        elif attrs['symbol'] == 'd':
                            if attrs['padding']:
                                tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                tempCtrl = tempCorrInfo['ctrl']
                                tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                                
                                temp = ctrl.intersections(prePos, tempCtrl, tempPos)[0]
                                if len(temp) and ctrl.lengthAt(temp[0]) < max(unit.x, unit.y):
                                    tempSplit = ctrl.splitting(temp[0])
                                    ctrlCorr['ctrl'] = tempSplit[1]
                                    ctrlCorr['pos'] = tempSplit[0].pos
                                    serif[0].append('s')
                                continue
                            elif attrs['dir'] == '3' and attrs['se'] == 1:
                                tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                if 'extend' in tempCorrInfo:
                                    tempCtrl = tempCorrInfo['ctrl']
                                    tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])

                                    tempT = tempCtrl.roots(y=prePos.y, pos=tempPos)[0]
                                    tempPos = tempCtrl.valueAt(tempT, pos=tempPos)
                                    tempVal = tempPos.x - prePos.x
                                    ctrlCorr['pos'] = bs.Point(tempVal, 0)
                                    ctrlCorr['ctrl'] = copy.deepcopy(ctrl)
                                    ctrlCorr['ctrl'].scale(bs.Point((ctrl.pos.x+tempVal)/ctrl.pos.x,1))
                                    ctrlCorr['tangents'] = tempCtrl.tangent(tempT, 10)
                                    serif[0].append('s3')
                                    break
                                raise 'undefine'
                            elif attrs['dir'] == '1' and attrs['se'] == 0:
                                if 'h' in serif[0]:
                                    continue
                                elif 'corr' in corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]:
                                    if ctrl.pos.x < unit.x * 1.5:
                                        continue
                                    tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                    tempTarget = -corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]['corr'].y / 2
                                    tempT = tempCorrInfo['ctrl'].roots(y=tempTarget)[0]
                                    tempTarget = tempCorrInfo['ctrl'].valueAt(tempT)
                                    tempTarget.x = abs(tempTarget.x)

                                    ctrlCorr['scale'] = bs.Point((tempTarget.x+abs(ctrl.pos.x))/ctrl.pos.x, (tempTarget.y+ctrl.pos.y)/ctrl.pos.y)
                                    ctrlCorr['startCorr'] = -tempTarget
                                    ctrlCorr['splitLine'] = tempCorrInfo['ctrl'].tangent(tempT, 10)
                                    serif[0].append('d')
                                    continue
                                elif 'v' in serif[0]:
                                    serif[0][serif[0].index('v')] = 'vd'
                                    continue
                                else:
                                    continue
                            elif attrs['dir'] == '1' and attrs['se'] == 1:
                                continue
                        raise 'undefine'
                    
                    for r in request:
                        if r not in serif[0]:
                            raise 'undefine'

                    if len(serif[0]) == 0:
                        serif[0] = 'yes'
                    elif len(serif[0]) > 1:
                        if serif[0] == ['h','v'] or serif[0] == ['v','h']:
                            serif[0] = 'hv'
                        else:
                            raise 'undefine'
                    else:
                        serif[0] = serif[0][0]

                if b:
                    request = []
                    for attrs in expInfo[1]['front']+expInfo[1]['back']:
                        if attrs['symbol'] == 'h':
                            if attrs['padding']:
                                serif[1].append('h')
                                continue
                            elif attrs['dir'] == '6' and attrs['se'] == 1:
                                serif[1].append('e6')
                                continue
                        elif attrs['symbol'] == 'v':
                            raise 'undefine'
                        elif attrs['symbol'] == 'd':
                            if attrs['padding']:
                                tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                tempCtrl = tempCorrInfo['ctrl']
                                tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])

                                tempT = ctrl.intersections(prePos, tempCtrl, tempPos)
                                if len(tempT[0]) and ctrl.reverse().lengthAt(1-tempT[0][0]) < max(unit.x, unit.y):
                                    ctrlCorr2['tangents'] = tempCtrl.tangents(tempT[1][0], 10, tempPos)
                                    serif[1].append('d')
                                continue
                            elif attrs['dir'] == '1' and attrs['se'] == 1:
                                continue
                            elif attrs['dir'] == '9' and attrs['se'] == 0:
                                continue
                            elif attrs['dir'] == '1' and attrs['se'] == 0:
                                # if 'h' in serif[1]:
                                    continue
                        raise 'undefine'
                    
                    for r in request:
                        if r not in serif[1]:
                            raise 'undefine'

                    if len(serif[1]) == 0:
                        serif[1] = 'yes'
                    elif len(serif[1]) > 1:
                        raise 'undefine'
                    else:
                        serif[1] = serif[1][0]

            if preDir == '*':
                if nectDir == '*':
                    check(True, True)
                    if ctrl.pos.x < unit.x * 1.6 and (indexCorr == 0 or dirAttrs[index-indexCorr] != '2'):
                        if (serif[0] == 'yes' or serif[0] == 'vd' or serif[0] == 'hv') and (serif[1] == 'yes' or serif[1] == 'd'):
                            comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                        elif serif[0] == 'h' and serif[1] == 'yes':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos+bs.Point(0, tempCorr), strokeWidth, '3')
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                                comp = comp.splitting(prePos, prePos+bs.Point(99, 0))[1][0]
                                comp.close()
                        elif serif[0] == 'd' and serif[1] == 'yes':
                            ctrl.scale(ctrlCorr['scale'])
                            prePos += ctrlCorr['startCorr']
                            comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                            comp = comp.splitting(prePos+ctrlCorr['splitLine'], prePos)[1][0]
                            comp.close()
                        elif serif[0] == 's' and serif[1] == 'yes':
                            comp, xcenter = comp_dot(ctrlCorr['ctrl'], prePos+ctrlCorr['pos'], strokeWidth, '3')
                        elif serif[0] == 'yes' and serif[1] == 'h':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                                temp = comp.splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y), connect=False)[0]
                                if len(temp) > 2: raise 'undefine'

                                comp = temp[0]
                                if len(temp) == 2:
                                    comp.connect(temp[1].startPos() - comp.endPos())
                                    comp.connectPath(temp[1])

                                comp.close()
                        elif serif[0] == 'yes' and serif[1] == 'e6':
                            comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3', bExtend=strokeWidth.x)
                        elif serif[0] == 'h' and serif[1] == 'h':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT*2)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos+bs.Point(0, tempCorr/2), strokeWidth, '3')
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3', fExtend=strokeWidth.x/2, bExtend=strokeWidth.x/2)
                                comp = comp.splitting(prePos, prePos+bs.Point(99, 0))[1][0]
                                comp.close()
                                comp = comp.splitting(currPos, currPos+bs.Point(99, 0))[0][0]
                                comp.close()
                        else:
                            raise 'undefine'
                    else:
                        if (serif[0] == 'yes' or serif[0] == 'h' or serif[0] == 'vd') and serif[1] == 'yes':
                            comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=16)
                        elif serif[0] == 'yes' and serif[1] == 'h':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                                temp = comp.splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y), connect=False)[0]
                                if len(temp) != 2: raise 'undefine'

                                comp = temp[0]
                                comp.connect(temp[1].startPos() - comp.endPos())
                                comp.connectPath(temp[1])
                                comp.close()
                        elif serif[0] == 'yes' and serif[1] == 'e6':
                            comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=strokeWidth.x)
                        elif serif[0] == 'yes' and serif[1] == 'd':
                            comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=strokeWidth.x)
                            comp = comp.splitting(ctrlCorr2['tangents'][0], ctrlCorr2['tangents'][1])[0][0]
                            comp.close()
                        elif serif[0] == 's' and serif[1] == 'yes':
                            comp, xcenter = comp_3(strokeWidth, ctrlCorr['ctrl'].lengthAt(1), 'all')
                            comp = bs.controlComp(ctrlCorr['ctrl'], comp, prePos+ctrlCorr['pos'], xcenter)
                        elif serif[0] == 's3' and serif[1] == 'yes':
                            comp, xcenter = comp_3(strokeWidth, ctrlCorr['ctrl'].pos.distance(), 'all')
                            comp = bs.controlComp(ctrlCorr['ctrl'], comp, prePos+ctrlCorr['pos'], xcenter)
                            # comp = comp.splitting(prePos+ctrlCorr['pos'], prePos+ctrlCorr['pos']+ctrlCorr['tangents'])[0][0]
                            # comp.close()
                        elif serif[0] == 'd' and serif[1] == 'yes':
                            ctrl.scale(ctrlCorr['scale'])
                            prePos += ctrlCorr['startCorr']
                            comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter)
                            comp = comp.splitting(prePos+ctrlCorr['splitLine'], prePos)[1][0]
                            comp.close()
                        elif serif[0] == 'v' and serif[1] == 'yes':
                            if diagonalInside(bpath.posIn(index-indexCorr), bpath.posIn(nectIndex), npath, index, cInfo):
                                comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                                comp = bs.controlComp(ctrl, comp, prePos, xcenter)
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '3')
                        elif serif[0] == 'hv' and serif[1] == 'yes':
                            if ctrl.pos.y > unit.y*2 and ctrl.pos.x < unit.x*2.5:
                                tempCorr = max(ctrl.pos.y / 2, min(DOT_IDENT, ctrl.pos.y))
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos + bs.Point(0, tempCorr*0.66), strokeWidth, '3')
                            else:
                                comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                                comp = bs.controlComp(ctrl, comp, prePos, xcenter)
                        else:
                            raise 'undefine'

                    pathList.append(comp)
                elif nectDir == '2':
                    comp, xcenter = comp_1(strokeWidth, ctrl.lengthAt(1), 'to')
                    comp = comp.mirror(bs.Point(), bs.Point(10, 0))
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, group=True)

                    parallelPath[0] = comp[0].reverse()
                    parallelPath[1] = bs.BezierPath()
                    parallelPath[1] = comp[1]
                    parallelPath[1].connectPath(comp[2])
                else:
                    raise 'undefine'
            elif nectDir == '*':
                if preDir == '2':
                    comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'to')
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter)
                    parallelPath[0].extend(comp)
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                elif preDir == '1':
                    check(False, True)

                    comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, bExtend=strokeWidth.x/2)
                    if serif[1] == 'd':
                        tempSplit = comp.splitting(ctrlCorr2['tangents'][0], ctrlCorr2['tangents'][1], connect=False)[0]
                        comp = tempSplit[0]
                        comp.connect(tempSplit[1].startPos() - comp.endPos())
                        comp.connectPath(tempSplit[1])

                    tempSplit = comp[-1].intersections(comp.posIn(-1), parallelPath[0][-1], parallelPath[0].posIn(-1))
                    if len(tempSplit[0]) and len(tempSplit[1]):
                        parallelPath[1].connect(parallelPath[0].endPos() - parallelPath[1].endPos())
                        parallelPath[1].append(parallelPath[0][-1].splitting(tempSplit[1][0])[1].reverse())
                        parallelPath[1].append(comp[-1].splitting(tempSplit[0][0])[0].reverse())
                    else:
                        tempSplit = comp[-1].splitting(comp[-1].roots(y=parallelPath[1].endPos().y, pos=comp.posIn(-1))[0])
                        parallelPath[1].connect(comp.posIn(-1) + tempSplit[0].pos - parallelPath[1].endPos())
                        parallelPath[1].append(tempSplit[0].reverse())

                    tempSplit = comp[1].intersections(comp.posIn(1), parallelPath[0][-1], parallelPath[0].posIn(-1))
                    parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[1][0])[0]
                    parallelPath[0].append(comp[1].splitting(tempSplit[0][0])[1])
                    parallelPath[0].extend(comp[2:-1])

                    parallelPath[0].connectPath(parallelPath[1].reverse())
                elif preDir == '9':
                    if not re.fullmatch(r'936?\*', dirAttrs):
                        raise 'undefine'
                
                    comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=strokeWidth.x/2)

                    tempCtrl = parallelPath[0][-1]
                    tempSplit = comp[1].splitting(comp[1].roots(x=strokeWidth.x/2)[0])
                    tempPos = [parallelPath[0].startPos(), comp.posIn(1)+tempSplit[0].pos]
                    tempTangen = tempSplit[1].tangent(0, 10) + tempPos[1]
                    tempPos.append(bs.intersection(tempPos[0], tempPos[0]+bs.Point(0, 10), tempPos[1], tempTangen))
                    parallelPath[0][-1] = angleInterpolation(tempPos[0], 0.5, tempPos[2], tempPos[1], 0.5)
                    parallelPath[0].append(tempSplit[1])
                    parallelPath[0].extend(comp[2:-1])
                    tempSplit = comp[-1].intersections(comp.posIn(-1), tempCtrl, tempPos[0])
                    parallelPath[0].append(comp[-1].splitting(tempSplit[0][0])[0])
                    parallelPath[0].append(tempCtrl.splitting(tempSplit[1][0])[1])
                    
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                else:
                    raise 'undefine'
                
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            else:
                if preDir == '2' and nectDir == '9':
                    comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance()+strokeWidth.x/2, 'bToA')
                    tempCtrl = copy.deepcopy(ctrl)
                    tempCtrl.pos += ctrl.tangent(1, strokeWidth.x/2)
                    comp = bs.controlComp(tempCtrl, comp, prePos, xcenter)
                    parallelPath[0].append(comp[0])
                    parallelPath[1].extend(comp.reverse()[:-1])
                elif preDir == '1' and (nectDir == '4' or nectDir == '2'):
                    comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                    comp.close()
                    comp = comp.mirror(bs.Point(), bs.Point(10, 0)).reverse()
                    
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, group=True)
                    comp = [comp[2], comp[3], comp[0], comp[1]]
                    parallelPath[1].connect(parallelPath[0].endPos() - parallelPath[1].endPos())

                    index = -1
                    for i in range(len(comp[-1])):
                        tempCtrl = comp[-1][index].reverse()
                        tempSplit = tempCtrl.intersections(comp[-1].endPos(), parallelPath[0][-1], parallelPath[0].posIn(-1))
                        if len(tempSplit[0]):
                            break
                        else:
                            index -= 1

                    parallelPath[1].append(parallelPath[0][-1].splitting(tempSplit[1][0])[1].reverse())
                    parallelPath[1].append(tempCtrl.splitting(tempSplit[0][0])[1])
                    parallelPath[1].extend(comp[-1].reverse()[-index:])

                    tempCtrl = comp[1][0]
                    tempSplit = tempCtrl.intersections(comp[1].startPos(), parallelPath[0][-1], parallelPath[0].posIn(-1))
                    parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[1][0])[0]
                    parallelPath[0].append(tempCtrl.splitting(tempSplit[0][0])[1])
                    parallelPath[1].extend(comp[1][1:])
                else:
                    raise 'undefine'
        elif dir == '1':
            expInfo = [
                extendedInfo(bpath.posIn(index-indexCorr), -bpath[index].pos, npath, index-indexCorr, cInfo, strokeWidth),
                extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, nectIndex-1, cInfo, strokeWidth)
            ]
            serif = [[],[]]
            ctrlCorr = {}

            def check(f, b):
                request = []
                if f:
                    for attrs in expInfo[0]['front']+expInfo[0]['back']:
                        # if attrs['indexes'] == [npath, index-indexCorr]: continue
                        if attrs['symbol'] == 'h':
                            if attrs['padding'] or (attrs['dir'] == '6' and attrs['se'] == 1):
                                serif[0].append('h')
                                continue
                            elif attrs['dir'] == '6' and attrs['se'] == 0:
                                serif[0].append('s6')
                                continue
                            raise 'undefine'
                        elif attrs['symbol'] == 'v':
                            if attrs['padding']:
                                serif[0].append('v')
                                continue
                            elif attrs['dir'] == '2' and attrs['se'] == 0:
                                if 'cd' in serif[0] or 'h' in serif[0]:
                                    continue
                                raise 'undefine'
                            elif attrs['dir'] == '2' and attrs['se'] == 1:
                                continue
                        elif attrs['symbol'] == 'd':
                            if attrs['padding']:
                                raise 'undefine'
                            elif attrs['dir'] == '3' and attrs['se'] == 0:
                                if 'corr' in corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]:
                                    tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                    tempTarget = -corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]['corr'].y / 2
                                    tempT = tempCorrInfo['ctrl'].roots(y=tempTarget)[0]
                                    tempTarget = tempCorrInfo['ctrl'].valueAt(tempT)
                                    tempTarget.x = -tempTarget.x

                                    ctrlCorr['scale'] = bs.Point((strokeWidth.x/2-tempTarget.x+abs(ctrl.pos.x))/abs(ctrl.pos.x), (tempTarget.y+ctrl.pos.y)/ctrl.pos.y)
                                    ctrlCorr['startCorr'] = -tempTarget
                                    ctrlCorr['splitLine'] = tempCorrInfo['ctrl'].tangent(tempT, 10)
                                    ctrlCorr['splitCorr'] = bs.Point(-strokeWidth.x/2, 0)
                                    serif[0].append('d')
                                    continue
                                elif 'v' in serif[0]:
                                    continue
                                else:
                                    ctrlCorr['fExtend'] = strokeWidth.x
                                    continue
                            elif attrs['dir'] == '3' and attrs['se'] == 1:
                                tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                if 'extend' in tempCorrInfo:
                                    tempCtrl = tempCorrInfo['ctrl']
                                    tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                                    tempT = ctrl.intersections(prePos, tempCtrl, tempPos)
                                    if len(tempT[0]):
                                        tempSplit = ctrl.splitting(tempT[0][0])
                                        ctrlCorr['ctrl'] = tempSplit[1]
                                        ctrlCorr['pos'] = tempSplit[0].pos
                                        ctrlCorr['tangents'] = tempCtrl.tangent(tempT[1][0], 10)
                                        serif[0].append('cd')
                                        continue
                                else:
                                    request.append('h')
                                    continue
                            elif attrs['dir'] == '1' and attrs['se'] == 1:
                                if 'v' in serif[0]:
                                    continue
                        raise 'undefine'
                    
                    for r in request:
                        if r not in serif[0]:
                            raise 'undefine'

                    if len(serif[0]) == 0:
                        serif[0] = 'yes'
                    elif len(serif[0]) > 1:
                        if serif[0] == ['h','v'] or serif[0] == ['v','h']:
                            serif[0] = 'hv'
                        else:
                            raise 'undefine'
                    else:
                        serif[0] = serif[0][0]

                request = []
                if b:
                    for attrs in expInfo[1]['front']+expInfo[1]['back']:
                        if attrs['symbol'] == 'v':
                            if attrs['padding']:
                                serif[1].append('v')
                                continue
                            elif attrs['dir'] == '2' and attrs['se'] == 0:
                                serif[1].append('e2')
                                continue
                        elif attrs['symbol'] == 'h':
                            if attrs['padding']:
                                serif[1].append('h')
                                continue
                            elif attrs['dir'] == '6' and attrs['se'] == 1:
                                serif[1].append('e6')
                                continue
                            elif attrs['dir'] == '6' and attrs['se'] == 0:
                                continue
                        elif attrs['symbol'] == 'd':
                            if attrs['padding']:
                                tempCorrInfo = corrList[attrs['indexes'][0]][str(attrs['indexes'][1])]
                                tempCtrl = tempCorrInfo['ctrl']
                                tempPos = tempCorrInfo.get('corr', bs.Point()) + cInfo['bpaths'][attrs['indexes'][0]].posIn(attrs['indexes'][1])
                                tempT = ctrl.intersections(prePos, tempCtrl, tempPos)[0]
                                if len(tempT):
                                    ctrlCorr['t'] = tempT[0]
                                    serif[1].append('de')
                                continue
                            elif attrs['dir'] == '1' and attrs['se'] == 0:
                                if 'v' in serif[1]:
                                    continue
                            elif attrs['dir'] == '9' and attrs['se'] == 1:
                                continue
                            elif attrs['dir'] == '3':
                                continue
                        raise 'undefine'
                    if len(serif[1]) == 0:
                        serif[1] = 'yes'
                    elif len(serif[1]) > 1:
                        if 'e2' in serif[1]:
                            serif[1].remove('e2')
                            if len(serif[1]) == 1 : serif[1] = serif[1][0]

                        if len(serif[1]) > 1:
                            raise 'undefine'
                    else:
                        serif[1] = serif[1][0]

                    for r in request:
                        if r not in serif[1]:
                            raise 'undefine'
                    
            if preDir == '*':
                if nectDir == '*':
                    check(True, True)
                    if abs(ctrl.pos.x) < unit.x * 1.5 and (indexCorr == 0 or dirAttrs[index-indexCorr] != '2') and serif[0] != 'd':
                        if (serif[0] == 'yes' or serif[0] == 'h' or serif[0] == 'v') and serif[1] == 'yes':
                            comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '1')
                        elif serif[0] == 'yes' and (serif[1] == 'yes' or serif[1] == 'v' or serif[1] == 'de'):
                            comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '1')
                        elif serif[0] == 'yes' and serif[1] == 'h':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '1')
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '1')
                                temp = comp.splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y), connect=False)[0]
                                if len(temp) > 2: raise 'undefine'

                                comp = temp[0]
                                if len(temp) == 2:
                                    comp.connect(temp[1].startPos() - comp.endPos())
                                    comp.connectPath(temp[1])

                                comp.close()
                        elif serif[0] == 'yes' and serif[1] == 'e2':
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter)
                        elif serif[0] == 'h' and serif[1] == 'h':
                            tempSplit = diagonalSplitInfo(bpath.posIn(index-indexCorr), bpath.posIn(nectIndex), npath, index, cInfo)
                            if len(tempSplit[1]) == 2:
                                if ctrl.pos.y > DOT_MIN_HEIGHT:
                                    tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT*2)
                                    ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                    comp, xcenter = comp_dot(ctrl, prePos+bs.Point(0, tempCorr/2), strokeWidth, '1')
                                else:
                                    raise 'undefine'
                            else:
                                tempVal = strokeWidth.x/2 / math.cos(ctrl.normals(0)[0].radian())
                                comp = bs.BezierPath()
                                comp.start(prePos - bs.Point(tempVal, 0))
                                comp.connect(bs.Point(tempVal*2, 0))
                                comp.append(ctrl)
                                comp.connect(bs.Point(-tempVal*2, 0))
                                comp.append(ctrl.reverse())
                                comp.close()
                        else:
                            raise 'undefine'
                    else:
                        if serif[1] == 'e2': serif[1] = 'yes'

                        if serif[0] == 'v' and serif[1] == 'v':
                            raise 'undefine'
                        elif serif[0] == 'yes' and (serif[1] == 'yes' or serif[1] == 'v' or serif[1] == 'e6'):
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=ctrlCorr.get('fExtend', 0))
                        elif serif[0] == 'yes' and serif[1] == 'h':
                            if ctrl.pos.y > DOT_MIN_HEIGHT:
                                tempCorr = min(ctrl.pos.y - DOT_MIN_HEIGHT, DOT_IDENT)
                                ctrl.scale(bs.Point(1, (ctrl.pos.y-tempCorr)/ctrl.pos.y))
                                comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'all')
                                comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=ctrlCorr.get('fExtend', 0))
                            else:
                                comp, xcenter = comp_dot(ctrl, prePos, strokeWidth, '1')
                                temp = comp.splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y), connect=False)[0]
                                if len(temp) > 2: raise 'undefine'

                                comp = temp[0]
                                if len(temp) == 2:
                                    comp.connect(temp[1].startPos() - comp.endPos())
                                    comp.connectPath(temp[1])

                                comp.close()
                        elif serif[0] == 'yes' and serif[1] == 'de':
                            tempCtrl = ctrl.splitting(ctrlCorr['t'])[0]
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'all')
                            comp = bs.controlComp(tempCtrl, comp, prePos, xcenter)
                        elif serif[0] == 'cd' and serif[1] == 'yes':
                            comp, xcenter = comp_1(strokeWidth, ctrlCorr['ctrl'].pos.distance(), 'to')
                            comp = bs.controlComp(ctrlCorr['ctrl'], comp, prePos+ctrlCorr['pos'], xcenter, fExtend=32)
                            comp.close()
                            comp = comp.splitting(prePos+ctrlCorr['pos'], prePos+ctrlCorr['pos']+ctrlCorr['tangents'])[1][0]
                            comp.close()
                        elif serif[0] == 'd' and serif[1] == 'yes':
                            ctrl.scale(ctrlCorr['scale'])
                            prePos += ctrlCorr['startCorr']
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                            comp = bs.controlComp(ctrl, comp, prePos-ctrlCorr['splitCorr'], xcenter, bExtend=32)
                            comp.close()
                            comp = comp.splitting(prePos, prePos+ctrlCorr['splitLine'])[1][0]
                            comp.close()
                        elif serif[0] == 'h' and serif[1] == 'yes':
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                            comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2)
                            comp.close()
                            if 'v' in serif[0]:
                                comp = comp.splitting(prePos, prePos+bs.Point(0, 10))[1][0]
                                comp.close()
                            if 'h' in serif[0]:
                                comp = comp.splitting(prePos, prePos+bs.Point(10, 0))[1][0]
                                comp.close()
                        elif (serif[0] == 'v' or serif[0] == 'hv') and serif[1] == 'yes':
                            comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                            if abs(ctrl.pos.x) < strokeWidth.x*3 and abs(ctrl.pos.x / ctrl.pos.y) < 0.5:
                                comp = bs.controlComp(bs.BezierCtrl(ctrl.pos), comp, prePos, xcenter, fExtend=strokeWidth.x/2)
                            else:
                                comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2)
                            comp.close()
                            if 'v' in serif[0]:
                                comp = comp.splitting(prePos, prePos+bs.Point(0, 10))[1][0]
                                comp.close()
                            if 'h' in serif[0]:
                                comp = comp.splitting(prePos, prePos+bs.Point(10, 0))[1][0]
                                comp.close()
                        elif serif[0] == 'h' and serif[1] == 'h':
                            raise 'undefine'
                        else:
                            raise 'undefine'

                    pathList.append(comp)
                elif nectDir == '6' or nectDir == '3':
                    check(True, False)
                    isSplit = len(diagonalSplitInfo(bpath.posIn(index-indexCorr), bpath.posIn(nectIndex), npath, index, cInfo)[1]) > 2

                    if serif[0] == 'yes' or serif[0] == 'h':
                        tempCtrl = copy.deepcopy(ctrl)
                        tempPos = bs.Point()
                        if serif[0] == 'h':
                            if ctrl.pos.y < strokeWidth.x*1.5: raise 'undefine'
                            tempCtrl.scale(bs.Point(1, (tempCtrl.pos.y-strokeWidth.x/2)/tempCtrl.pos.y))
                            tempPos = bs.Point(0, strokeWidth.x/2)

                        if isSplit:
                            comp, xcenter = comp_1(strokeWidth, tempCtrl.pos.distance(), 'allTo')
                            comp = bs.controlComp(tempCtrl, comp, prePos+tempPos, xcenter, group=True, bExtend=strokeWidth.x*0.72)
                        else:
                            comp, xcenter = comp_1(strokeWidth, tempCtrl.pos.distance(), 'all')
                            comp = bs.controlComp(tempCtrl, comp, prePos+tempPos, xcenter, group=True, bExtend=strokeWidth.x*0.72)

                        parallelPath[0].start(comp[0].startPos())
                        parallelPath[0].extend(comp[0])
                        parallelPath[0].extend(comp[1])
                        parallelPath[0].extend(comp[2])
                        parallelPath[1].start(comp[0].startPos())
                        parallelPath[1].extend(comp[-1].reverse())
                    elif serif[0] == 's6':
                        STROKE = stroke_2(strokeWidth, 's6')
                        comp, xcenter = comp_rect(strokeWidth.x)
                        comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, bExtend=strokeWidth.x/2)

                        parallelPath[0].start(comp.startPos())
                        parallelPath[0].connect(prePos + bs.Point(strokeWidth.x/-2+STROKE['h'], 0) - comp.startPos())
                        tempSplit = comp[1].splitting(comp[1].roots(y=prePos.y, pos=comp.posIn(1))[0])
                        parallelPath[0].connect(comp.posIn(1) + tempSplit[0].pos - parallelPath[0].endPos())
                        parallelPath[0].append(tempSplit[1])
                        parallelPath[1].start(comp.startPos())
                        parallelPath[1].append(comp[-1].reverse())
                    else:
                        raise 'undefine'
                elif nectDir == '9':
                    check(True, False)

                    if serif[0] == 'h':
                        comp, xcenter = comp_rect(strokeWidth.x)
                        comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x, bExtend=strokeWidth.x)
                        comp = comp.splitting(prePos, prePos+bs.Point(10, 0))[1][0]

                        parallelPath[0].start(comp.startPos())
                        parallelPath[0].append(comp[0])
                        parallelPath[1].start(comp.endPos())
                        parallelPath[1].append(comp[-1].reverse())
                    else:
                        raise 'undefine'
                else:
                    raise 'undefine'
            elif nectDir == '*':
                if preDir == '6':
                    check(False, True)
                    if serif[1] == 'e2': serif[1] = 'yes'

                    if serif[1] == 'yes' or serif[1] == 'h':
                        comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                        comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, group=True)

                        tempPos = [
                            parallelPath[0].posIn(-1),
                            comp[0].posIn(0),
                        ]
                        tempVal = tempPos[0].y+parallelPath[0][-1].pos.y
                        if tempPos[1].y > tempVal:
                            tempPos.append(comp[0].startPos())
                            parallelPath[0][-1] = ellipticalArc(tempPos[2].x-tempPos[0].x, tempPos[2].y-tempPos[0].y, False)
                            parallelPath[0].extend(comp[0])
                            parallelPath[0].extend(comp[1])
                        else:
                            tempSplit = comp[0].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                            tempPos.append(tempSplit.startPos())
                            parallelPath[0][-1] = ellipticalArc(tempPos[2].x-tempPos[0].x, tempPos[2].y-tempPos[0].y, False)
                            parallelPath[0].extend(tempSplit)
                            parallelPath[0].extend(comp[1])

                        tempVal = parallelPath[1].endPos().y
                        tempSplit = comp[-1].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                        parallelPath[1][-1].pos.x += tempSplit.endPos().x - parallelPath[1].endPos().x
                        parallelPath[1].extend(tempSplit.reverse())

                        if serif[1] == 'h':
                            temp = parallelPath[0].splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y))[0]
                            if len(temp) != 1: raise 'undefine'
                            parallelPath[0] = temp[0]
                            temp = parallelPath[1].splitting(bs.Point(0, currPos.y), bs.Point(10, currPos.y))[0]
                            if len(temp) != 1: raise 'undefine'
                            parallelPath[1] = temp[0]

                            parallelPath[0].connect(parallelPath[1].endPos() - parallelPath[0].endPos())
                    elif serif[1] == 'de':
                        tempCtrl = ctrl.splitting(ctrlCorr['t'])[0]
                        comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                        comp = bs.controlComp(tempCtrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, group=True)
                        
                        tempPos = [
                            parallelPath[0].posIn(-1),
                            comp[0].posIn(0),
                        ]
                        tempVal = tempPos[0].y+parallelPath[0][-1].pos.y
                        tempSplit = comp[0].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                        tempPos.append(tempSplit.startPos())
                        parallelPath[0][-1] = ellipticalArc(tempPos[2].x-tempPos[0].x, tempPos[2].y-tempPos[0].y, False)
                        parallelPath[0].extend(tempSplit)
                        parallelPath[0].extend(comp[1])

                        tempVal = parallelPath[1].endPos().y
                        tempSplit = comp[-1].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                        parallelPath[1][-1].pos.x += tempSplit.endPos().x - parallelPath[1].endPos().x
                        parallelPath[1].extend(tempSplit.reverse())
                    elif serif[1] == 'e6':
                        comp, xcenter = comp_rect(strokeWidth.x)
                        comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, bExtend=strokeWidth.x/2)

                        tempPos = [
                            parallelPath[0].posIn(-1),
                            comp.posIn(1),
                        ]
                        tempSplit = comp[1].splitting(comp[1].roots(y=tempPos[0].y+parallelPath[0][-1].pos.y, pos=tempPos[1])[0])
                        tempPos.append(tempPos[1]+tempSplit[0].pos)
                        parallelPath[0][-1] = ellipticalArc(tempPos[2].x-tempPos[0].x, tempPos[2].y-tempPos[0].y, False)
                        parallelPath[0].append(tempSplit[1])
                        parallelPath[0].append(comp[2])
                        
                        tempSplit = comp[-1].splitting(comp[-1].roots(y=parallelPath[1].endPos().y, pos=comp.posIn(-1))[0])
                        parallelPath[1].append(tempSplit[0].reverse())
                    else:
                        raise 'undefine'
                    
                    parallelPath[0].connectPath(parallelPath[1].reverse())
                elif preDir == '2':
                    check(False, True)
                    if serif[1] == 'e2': serif[1] = 'yes'

                    comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=32)
                    if serif[1] == 'h':
                        comp = comp.splitting(currPos, currPos+bs.Point(10, 0), connect=False)[0]
                        parallelPath[0].connectPath(comp[0])
                        parallelPath[1].connectPath(comp[-1].reverse())
                        parallelPath[0].connect(parallelPath[1].endPos() -parallelPath[0].endPos())
                    else:
                        parallelPath[0].extend(comp)

                    parallelPath[0].connectPath(parallelPath[1].reverse())
                else:
                    raise 'undefine'
                
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif preDir == '6' and nectDir == '2':
                if dirAttrs[nectIndex:] == '268*':
                    tempCtrl = angleInterpolation(prePos, 0.66, currPos-bs.Point(0, ctrl.pos.y/4), currPos, 0.66)
                    comp, xcenter = comp_rect(strokeWidth.x)
                    comp = bs.controlComp(tempCtrl, comp, prePos, xcenter, fExtend=32)

                    tempPos = [
                        parallelPath[0].posIn(-1),
                        comp.posIn(1),
                    ]
                    tempVal = tempPos[0].y+parallelPath[0][-1].pos.y
                    if tempPos[1].y > tempVal:
                        parallelPath[0][-1] = ellipticalArc(tempPos[1].x-tempPos[0].x, tempPos[1].y-tempPos[0].y, False)
                        parallelPath[0].append(comp[1])
                    else:
                        tempSplit = comp[1].splitting(comp[1].roots(y=parallelPath[0].endPos().y, pos=comp.posIn(1))[0])
                        tempPos = [parallelPath[0].posIn(-1), comp.posIn(1)+tempSplit[0].pos]
                        parallelPath[0][-1] = ellipticalArc(tempPos[1].x - tempPos[0].x, tempPos[1].y - tempPos[0].y, False)
                        parallelPath[0].append(tempSplit[1])

                    tempSplit = comp[-1].splitting(comp[-1].roots(y=parallelPath[1].endPos().y, pos=comp.posIn(-1))[0])
                    parallelPath[1][-1].pos.x += comp.startPos().x - tempSplit[1].pos.x - parallelPath[1].endPos().x
                    parallelPath[1].append(tempSplit[0].reverse())
                else:
                    raise 'undefine'
            elif preDir == '6' and (nectDir == '6' or nectDir == '3'):
                comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'to')
                comp = bs.controlComp(ctrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2, bExtend=strokeWidth.x*0.66, group=True)

                tempVal = parallelPath[0].endPos().y
                tempSplit = comp[0].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                tempPos = [parallelPath[0].posIn(-1), tempSplit.startPos()]
                parallelPath[0][-1] = ellipticalArc(tempPos[1].x - tempPos[0].x, tempPos[1].y - tempPos[0].y, False)
                parallelPath[0].extend(tempSplit)

                tempVal = parallelPath[1].endPos().y
                tempSplit = comp[-1].splitting(bs.Point(0, tempVal), bs.Point(10, tempVal))[1][0]
                parallelPath[1][-1].pos.x += tempSplit.endPos().x  - parallelPath[1].endPos().x
                parallelPath[1].extend(tempSplit.reverse())
            else:
                raise 'undefine'
        elif dir == '9':
            if preDir == '*' and nectDir == '*':
                expInfo = extendedInfo(bpath.posIn(index-indexCorr), -bpath[index].pos, npath, index-indexCorr, cInfo, strokeWidth)
                temp = diagonalInside(bpath.posIn(index-indexCorr), bpath.posIn(nectIndex), npath, index, cInfo)
                for attrs in expInfo['front']+expInfo['back']:
                    temp = False

                if abs(ctrl.pos.y) < unit.y * 1.5 and abs(ctrl.pos.x) > unit.x * 3.5 and temp:
                    comp = comp_6(strokeWidth, ctrl, prePos)
                else:
                    comp, xcenter = comp_1(strokeWidth, ctrl.pos.distance(), 'all')
                    comp = comp.mirror(bs.Point(), bs.Point(0, 10))
                    xcenter = 1 - xcenter
                    comp = bs.controlComp(ctrl, comp, prePos, xcenter, bExtend=strokeWidth.x/2)

                pathList.append(comp)
            elif preDir == '*' and nectDir == '2':
                STROKE = stroke_9(strokeWidth, 'to')

                comp = comp_6(strokeWidth, ctrl, prePos)
                parallelPath[0] = bs.BezierPath()
                parallelPath[0].start(comp.startPos())
                parallelPath[1] = bs.BezierPath()
                parallelPath[1].start(comp.startPos())

                parallelPath[0].extend(comp[:2])
                tempPos = [
                    parallelPath[0].endPos(),
                    currPos + bs.Point(strokeWidth.x/2, STROKE['v'][0])
                ]
                tempPos.append(bs.Point(tempPos[1].x + STROKE['h'][0], tempPos[0].y + (tempPos[1].y - tempPos[0].y) * STROKE['dot']))
                parallelPath[0].extend(pointAndTangent(bs.Point(0, 10), tempPos[0], tempPos[2], tempPos[1], STROKE['ratio'][0], STROKE['ratio'][1]).splitting(STROKE['ratio'][1]))

                parallelPath[1].append(comp[-1].reverse())
                parallelPath[1].append(comp[-2].reverse())
                parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].roots(x=currPos.x-strokeWidth.x/2, pos=parallelPath[1].posIn(-1))[0])[0]
            elif preDir == '*' and nectDir == '3':
                if ctrl.pos.x > unit.x*1.5 or ctrl.pos.y > unit.y*1.5:
                    raise 'undefine'
                
                comp, xcenter = comp_3(strokeWidth, ctrl.pos.distance(), 'all')
                comp = comp.mirror(bs.Point(), bs.Point(10, 0))
                tempCtrl = angleInterpolation(prePos, 0.5, bs.Point(currPos.x, (prePos.y+currPos.y)/2), currPos-bs.Point(0, 32), 0.6)
                comp = bs.controlComp(tempCtrl, comp, prePos, xcenter, fExtend=strokeWidth.x/2)

                parallelPath[1] = bs.BezierPath()
                parallelPath[1].start(comp.startPos())
                parallelPath[1].extend(comp[:-1])
                parallelPath[0] = bs.BezierPath()
                parallelPath[0].start(comp.startPos())
                parallelPath[0].append(comp[-1].reverse())
            elif preDir == '3' and nectDir == '*':
                tempPos = ctrl.pos.normalization(strokeWidth.x).perpendicular() + prePos
                tempSplit = parallelPath[0][-1].intersections(parallelPath[0].posIn(len(parallelPath[0])-1), bs.BezierCtrl((tempPos - currPos) * 2), currPos)
                parallelPath[0][-1] = parallelPath[0][-1].splitting(tempSplit[0][0])[0]
                
                STROKE = stroke_9(strokeWidth, 'hook')
                tempTangen = ctrl.pos.perpendicular().normalization(STROKE['head'])

                tempPos = [parallelPath[0].endPos(), currPos + tempTangen/2]
                tempPos.append(bs.intersection(tempPos[0], parallelPath[0][-1].tangent(1, 32)+tempPos[0], tempPos[1], tempPos[1] + ctrl.pos))
                parallelPath[0].append(angleInterpolation(tempPos[0], STROKE['left'][0], tempPos[2], tempPos[1], STROKE['left'][1]))
                parallelPath[0].connect(-tempTangen)
                
                tempPos = [parallelPath[1].endPos(), parallelPath[0].endPos()]
                tempPos.append(sinInterpolation(STROKE['right'][0], STROKE['right'][1], tempPos[0], tempPos[1], prePos - tempTangen/2))
                parallelPath[0].append(threePointCtrl(tempPos[1], tempPos[2], tempPos[0]))
                
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif (preDir == '2' or preDir == '1') and nectDir == '*':
                STROKE = stroke_9(strokeWidth, 'dir')
                tempTangen = ctrl.pos.perpendicular().normalization()
                tempLine = [prePos+tempTangen*STROKE['v'][0], currPos+tempTangen*STROKE['head']/2]
                parallelPath[0] = parallelPath[0].splitting(tempLine[0], tempLine[1])[0][0]
                parallelPath[1] = parallelPath[1].splitting(tempLine[0], tempLine[1])[0][0]

                parallelPath[0].connect(tempLine[1] - parallelPath[0].endPos())
                parallelPath[0].connect(-tempTangen * STROKE['head'])

                tempPos = [parallelPath[1].endPos()]
                tempVal = parallelPath[1][-1].lengthAt(1)
                parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].inDistance((tempVal-STROKE['v'][1])/tempVal))[0]
                tempPos.append(tempPos[0] + (tempLine[0]-tempLine[1]).normalization() * STROKE['h'][0])
                temp = parallelPath[1][-1].tangents(1, pos=parallelPath[1].endPos())
                tempPos.append(bs.intersection(temp[0], temp[1], tempPos[1], tempPos[1]+tempLine[0]-tempLine[1]))
                parallelPath[1].append(angleInterpolation(parallelPath[1].endPos(), STROKE['ratio'][0], tempPos[0], tempPos[1], STROKE['ratio'][1]))

                tempPos = [parallelPath[1].endPos(), parallelPath[0].endPos()]
                tempPos.append(bs.intersection(tempPos[0], tempPos[0]+tempTangen, tempPos[1], tempPos[1]+ctrl.pos))
                parallelPath[1].connect(tempPos[2] - tempPos[0])
                
                # tempTangen = tempTangen * STROKE['v'][2] + (tempPos[1] - tempPos[2]).normalization() * STROKE['h'][1]
                # parallelPath[1].append(threePointCtrl(tempPos[2], tempPos[2] + tempTangen, tempPos[1]))
                parallelPath[1].append(threePointCtrl(tempPos[2], sinInterpolation(0.5, 0.24, tempPos[2], currPos, tempPos[1]), tempPos[1]))
                
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif preDir == '8' and nectDir == '*':
                STROKE = stroke_8(strokeWidth, 'above')

                tempNormal = ctrl.pos.perpendicular().normalization()
                tempPos = [
                    parallelPath[0].endPos(),
                    currPos + tempNormal * STROKE['v'][0]
                ]
                tempPos.append(bs.intersection(tempPos[0], tempPos[0]+bs.Point(10,0), tempPos[1], tempPos[1] - ctrl.pos))
                tempCtrl = angleInterpolation(tempPos[0], 0.8, tempPos[2], tempPos[1], 1)
                tempCtrl = tempCtrl.radianSegmentation(abs((tempPos[1] - tempPos[2]).radian()) / 2)[0]
                parallelPath[0].extend(tempCtrl)
                parallelPath[0].connect(tempNormal * -STROKE['v'][0] * 2)

                tempPos = [
                    parallelPath[1].endPos(),
                    parallelPath[0].endPos(),
                ]
                tempPos.append(bs.intersection(tempPos[0], tempPos[0]+parallelPath[1][-1].tangent(1, 32), tempPos[1], tempPos[1] - ctrl.pos))
                parallelPath[1].append(angleInterpolation(tempPos[0], 1, tempPos[2], tempPos[1], 0.8))

                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            else:
                raise 'undefine'
        elif dir == '4':
            STROKE = stroke_4(strokeWidth, 'hook')
            expInfo = extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, index, cInfo, strokeWidth)
            pathLen = min(-ctrl.pos.x + expInfo.get('extend', 9999), unit.x*2.5)
            
            serif = 'yes'
            if pathLen >= STROKE['length']:
                pathLen = STROKE['length']
            elif pathLen < STROKE['length']*.6:
                serif = 'small'
            
            if preDir == '2' and nectDir == '*':
                if serif == 'yes':
                    parallelPath[0][-1].pos.y -= STROKE['v'][0]
                    parallelPath[0].append(ellipticalArc(-STROKE['h'][0], STROKE['v'][1], False))
                    parallelPath[0].append(angleInterpolation(bs.Point(), STROKE['ratio'][0], bs.Point(0, STROKE['v'][2]-STROKE['v'][1]), bs.Point(STROKE['h'][0]-pathLen, STROKE['v'][2]-STROKE['v'][1]), STROKE['ratio'][1]))
                    parallelPath[0].connect(bs.Point(0, -STROKE['v'][2]))

                    if parallelPath[1][-1].pos.y > STROKE['v'][0] + STROKE['h'][1]:
                        parallelPath[1][-1].pos.y -= STROKE['v'][0] + STROKE['h'][1]
                        parallelPath[1].append(ellipticalArc(-STROKE['h'][1], STROKE['h'][1], False))
                    else:
                        parallelPath[1].popBack()
                        parallelPath[1].append(ellipticalArc(-STROKE['h'][1], parallelPath[0].endPos().y-parallelPath[1].endPos().y, False))
                    parallelPath[1].connect(parallelPath[0].endPos() - parallelPath[1].endPos())
                else:
                    parallelPath[0].append(ellipticalArc(-strokeWidth.x, strokeWidth.y/2 + STROKE['v'][3], False))
                    tempPos = parallelPath[0].endPos() - parallelPath[1].endPos() - bs.Point(0, STROKE['v'][3])
                    parallelPath[1][-1].pos.y += strokeWidth.y/2 + STROKE['v'][3]

            elif preDir == '3' and nectDir == '*':
                if serif == 'small':
                    raise 'undefine'

                parallelPath[0].append(ellipticalArc(-STROKE['h'][0], STROKE['v'][1], False))
                parallelPath[0].append(angleInterpolation(bs.Point(), STROKE['ratio'][0], bs.Point(0, STROKE['v'][2]-STROKE['v'][1]), bs.Point(STROKE['h'][0]-pathLen, STROKE['v'][2]-STROKE['v'][1]), STROKE['ratio'][1]))
                parallelPath[0].connect(bs.Point(0, -STROKE['v'][2]))
                
                tempVal = parallelPath[1][-1].lengthAt(1)
                parallelPath[1][-1] = parallelPath[1][-1].splitting(parallelPath[1][-1].inDistance((tempVal-STROKE['v'][0])/tempVal))[0]
                tempPos = [
                    parallelPath[1].endPos(),
                    parallelPath[0].endPos(),
                ]
                tempPos.append(bs.intersection(tempPos[0], tempPos[0]+parallelPath[1][-1].tangent(1, 10), tempPos[1], tempPos[1]+bs.Point(10,0)))
                parallelPath[1].append(angleInterpolation(tempPos[0], 0.8, tempPos[2], tempPos[1], 0.8))
            else:
                raise 'undefine'
            
            parallelPath[0].connectPath(parallelPath[1].reverse())
            parallelPath[0].close()
            pathList.append(parallelPath[0])
        elif dir == '8':
            if preDir == '6' and nectDir == '*':
                STROKE = stroke_8(strokeWidth, 'hook')
                expInfo = extendedInfo(bpath.posIn(nectIndex), bpath[index].pos, npath, index, cInfo, strokeWidth)
                pathLen = -ctrl.pos.y + expInfo.get('extend', 9999)
                
                if pathLen > STROKE['length']:
                    pass
                # elif pathLen / STROKE['length'] < 0.5:
                #     raise 'undefine'
                pathLen = min(STROKE['length'], unit.y*2 - strokeWidth.y)
            
                tempOffset = bs.Point(STROKE['h'][0]/2, 0)
                # currPos.y = min(currPos.y, prePos.y-pathLen)
                currPos.y = prePos.y-pathLen

                tempPos = currPos-tempOffset-parallelPath[0].endPos()
                tempCtrl = angleInterpolation(bs.Point(), 0.85, bs.Point(tempPos.x, 0), tempPos, 1.0)
                parallelPath[0].extend(tempCtrl.radianSegmentation(math.pi/4)[0])

                tempPos = currPos+tempOffset-parallelPath[1].endPos()
                tempCtrl = bs.BezierCtrl(p1=bs.Point(-10,0), p2=bs.Point(tempPos.x, -10), pos=tempPos)
                tempCtrl, tempT = tempCtrl.threeTangentCurver(bs.Point(1,1), bs.Point(-STROKE['h'][1], -STROKE['v'][1]), tVal=True, none=False)
                tempCtrl = tempCtrl.splitting(tempT)
                parallelPath[1].extend(tempCtrl)

                parallelPath[0].connect(parallelPath[1].endPos()-parallelPath[0].endPos())
                parallelPath[0].connectPath(parallelPath[1].reverse())
                parallelPath[0].close()
                pathList.append(parallelPath[0])
            elif preDir == '*' and nectDir == '9':
                STROKE = stroke_8(strokeWidth, 'above')

                parallelPath[0] = bs.BezierPath()
                parallelPath[0].start(prePos)
                parallelPath[1] = bs.BezierPath()
                parallelPath[1].start(prePos)

                temp = ctrl.pos.y / 2
                tempT = 0.5
                tempCtrl = pointAndTangent(bs.Point(1,0), bs.Point(-STROKE['h'][0], temp), bs.Point(), bs.Point(STROKE['h'][1], temp), 0.8, tempT)
                tempSplit = tempCtrl.splitting(tempT)

                parallelPath[0].append(tempSplit[0].reverse())
                tempPos = [
                    parallelPath[0].endPos(),
                    currPos + bs.Point(-min(unit.x, STROKE['length']), STROKE['v'][0])
                ]
                tempPos.append(bs.intersection(tempPos[0], tempPos[0]+parallelPath[0][-1].tangent(1, 10), tempPos[1], tempPos[1]+bs.Point(10,0)))
                parallelPath[0].append(angleInterpolation(tempPos[0], 0.5, tempPos[2], tempPos[1], 0.9))
                parallelPath[0].connect(bs.Point(0, -STROKE['v'][0]*2))

                parallelPath[1].append(tempSplit[1])
            else:
                raise 'undefine'
        else:
            raise 'undefine'

        preDir = dir
        prePos = currPos
        indexCorr = nectIndex - index - 1
        index = nectIndex

    for path in pathList:
        if not path.isClose():
            raise Exception('Path is not closed!')

    return pathList

def testChar(char):
    data = fas.loadJson(DATA_FILE)
    charInfo = fas.genCharData(data[char], FONT_SIZE)
    charInfo['unit'] = bs.Point(charInfo['scale']['h'], charInfo['scale']['v']) * FONT_SIZE
    cList = lineCorrList(charInfo)

    shapes = []
    for i, bpath in enumerate(charInfo['bpaths']):
        shape = bs.BezierShape()
        shape.extend(toStrokes(bpath, charInfo, i, cList, char))
        shape.transform(move=bs.Point(FONT_SIZE * (1-GLYPFH_WIDTH) / 2))
        shapes.append(shape)

    fas.writeTempGlyphFromShapes(shapes, TEMP_GLYPH_FILE, 'svg', GLYPH_ATTRIB)

def testAllChar():
    if not os.path.exists(TEST_GLYPHS_DIR):
        os.mkdir(TEST_GLYPHS_DIR)
    else:
        for f in os.listdir(TEST_GLYPHS_DIR):
            file_path = os.path.join(TEST_GLYPHS_DIR, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

    data = fas.loadJson(DATA_FILE)
    for char, kpath in data.items():
        charInfo = fas.genCharData(kpath, FONT_SIZE)
        charInfo['unit'] = bs.Point(charInfo['scale']['h'], charInfo['scale']['v']) * FONT_SIZE
        cList = lineCorrList(charInfo)

        shapes = []
        for i, bpath in enumerate(charInfo['bpaths']):
            shape = bs.BezierShape()
            shape.extend(toStrokes(bpath, charInfo, i, cList, char))
            shape.transform(move=bs.Point(FONT_SIZE * (1-GLYPFH_WIDTH) / 2))
            shapes.append(shape)

        fas.writeTempGlyphFromShapes(shapes, os.path.join(TEST_GLYPHS_DIR, '%s.svg' % char), 'svg', GLYPH_ATTRIB)

def importGlyphs():
    import fontforge
    font = fontforge.open("config.sfd")
    font.version = FONT_VARSION
    font.createChar(32).width = int(FONT_SIZE/2) #空格

    data = fas.loadJson(DATA_FILE)
    errorList = {}
    charList = []
    num = len(data)
    count = 0
    
    for name, attrs in data.items():
        char = name
        code = ord(char)
        if code < 128:
            width = int(CHAR_WIDTH / 2)
        else:
            width = CHAR_WIDTH
        
        count += 1
        print("(%d/%d)%s: import glyph '%s' %d" % (count, num, font.fontname, char, code))
        
        charInfo = fas.genCharData(attrs, FONT_SIZE)
        charInfo['unit'] = bs.Point(charInfo['scale']['h'], charInfo['scale']['v']) * FONT_SIZE
        cList = lineCorrList(charInfo)

        shapes = []
        try:
            for i, bpath in enumerate(charInfo['bpaths']):
                shape = bs.BezierShape()
                shape.extend(toStrokes(bpath, charInfo, i, cList, char))
                shape.transform(move=bs.Point((CHAR_WIDTH - FONT_SIZE * GLYPFH_WIDTH) / 2))
                shapes.append(shape)
            charList.append(name)
        except Exception as e:
            errorList[char] = e
            print(char, e)
            continue
        
        fas.writeTempGlyphFromShapes(shapes, TEMP_GLYPH_FILE, 'svg', GLYPH_ATTRIB)
        glyph = font.createChar(code)
        glyph.importOutlines(TEMP_GLYPH_FILE)
        glyph.width = width
        
    fileList = os.listdir(SYMBOLS_DIR)
    num = len(fileList)
    symCount = 0
    for filename in fileList:
        filePath = '%s/%s' % (SYMBOLS_DIR, filename)
        if(filename[-4:] == '.svg'):
            if(filename[:-4].isdecimal()):
                n = int(filename[:-4])
                char = chr(n)
                code = n
                width = int(float(svgfile.parse(filePath).getroot().attrib['viewBox'].split()[2]))
            else:
                continue

            symCount += 1
            print("(%d/%d)%s: import symbol glyph '%s' %d from %s" % (symCount, num, font.fontname, char, code, filename))
            
            try:
                glyph = font.createChar(code)
                glyph.importOutlines(filePath)
                glyph.width = width
            except Exception as e:
                errorList[filename] = e
                print(filename, e)

    if len(errorList):
        print("\n%d glyphs with errors!" % len(errorList))
        for name, e in errorList.items():
            print(name, e)

    font.selection.all()
    font.removeOverlap()
    
    with open('char_list.txt', 'w') as f:
        f.write(''.join(charList))

    print("\n%s: The Font has %d glyphs" % (font.fontname, count + symCount - len(errorList)))
    print("Generate font file in %s\n" % (font.fontname + ".otf"))
    
    font.generate(font.fontname + ".otf")
    # font.generate(font.fontname + ".ttf")
    font.save(font.fontname + ".sfd")
    font.close()

    os.remove(TEMP_GLYPH_FILE)

if __name__ == '__main__':
    importGlyphs()
    testChar('乾') # 今学龸灬夬父幺万方乙𠂆子八丸奂及井夫九失工车亼象力𠂇阝纟龰金生夬矛予豕
    # testAllChar()
# 啊嗉愫瘰祁穵素累縠耶蓄螂邗邙邝邡邢那邦邪邬邮邯邰邳邵邶邸邹邺邻郁郄郅郊郏郐郑郗郢郤郧郭郾郿酃阞队阡防阳阶阼阽陉陌骡