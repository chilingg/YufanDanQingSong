from clsvg import bezierShape as bs

STROKE_WIDTH_LIST = {
    'y': 32,
    'x': 64,
}

DOT_MIN_HEIGHT = 96
DOT_IDENT = 32

yRatio = 1

def ellipticalArc(width, height, x):
    pos = bs.Point(width, height)
    if x:
        p1 = bs.Point(width * bs.SEMICIRCLE, 0)
        p2 = bs.Point(width, height * (1 - bs.SEMICIRCLE))
    else:
        p1 = bs.Point(0, height * bs.SEMICIRCLE)
        p2 = bs.Point(width * (1 - bs.SEMICIRCLE), height)

    return bs.BezierCtrl(pos, p1, p2)

def getStrokeWidth(unit):
    sWidth = {
        'y': STROKE_WIDTH_LIST['y'],
        'x': STROKE_WIDTH_LIST['x'],
    }

    if unit.x < STROKE_WIDTH_LIST['x']:
        if unit.x > STROKE_WIDTH_LIST['x']/2:
            sWidth['x'] = unit.x
        else:
            raise 'undefine'
        
    if unit.y < STROKE_WIDTH_LIST['x']:
        if unit.y > STROKE_WIDTH_LIST['x']/2:
            global yRatio
            yRatio = min(unit.x, unit.y) / STROKE_WIDTH_LIST['x']
            sWidth['x'] = min(yRatio*1.2, 1) * STROKE_WIDTH_LIST['x']
    if unit.y < STROKE_WIDTH_LIST['y']:
        raise 'undefine'
    

    return sWidth

def stroke_6(strokeWidth, sym):
    H_VAL_1 = 48
    H_VAL_2 = 64
    V_VAL_1 = 48

    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']
    if sym == 'f':
        return {
            'length': 16 * yRatio
        }
    elif sym == 'b':
        return {
            'h': [
                H_VAL_1 * xRatio,
                H_VAL_2 * xRatio,
                16 * xRatio
            ],
            'v': [
                V_VAL_1 * yRatio,
                16 * yRatio
            ]
        }
    elif sym == 'below':
        return {
            'h': [
                H_VAL_1 * xRatio,
                H_VAL_2 * xRatio
            ],
            'v': [
                V_VAL_1 * yRatio,
                54 * yRatio,
                24 * yRatio
            ]
        }
    elif sym == 'above':
        return {
            'h': [
                10 * xRatio,
                20 * xRatio,
                64 * xRatio,
                10 * xRatio,
            ],
            'v': [
                82 * xRatio,
                32 * xRatio,
                78 * xRatio,
                72 * xRatio,
                32 * xRatio,
            ]
        }
    else:
        raise 'undefine'

def stroke_2(strokeWidth, sym):
    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']
    if sym == 'f':
        return {
            'h': [
                32 * xRatio
            ],
            'v': [
                24 * yRatio,
                28 * yRatio
            ]
        }
    elif sym == 'b':
        return {
            'length': 24 * yRatio
        }
    elif sym == 's6':
        return {
            'h': 96 * xRatio,
            'v': 48 * yRatio
        }
    elif sym == 'e6':
        return {
            'v': [
                24 * yRatio,
                32 * yRatio
            ]
        }
    else:
        raise 'undefine'
    
def stroke_9(strokeWidth, sym):
    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']
    if sym == 'hook':
        return {
            'head': 16 * xRatio,
            'left': [
                0.9,
                0.1
            ],
            'right': [
                0.8,
                0.8
            ]
        }
    elif sym == 'dir':
        return {
            'head': 16 * xRatio,
            'h': [
                56 * xRatio,
                32 * xRatio
            ],
            'v': [
                64 * xRatio,
                38 * xRatio,
                8 * xRatio
            ],
            'ratio': [
                0.8,
                0.5
            ]
        }
    elif sym == 'to':
        return {
            'dot': 0.666,
            'h': [
                28 * xRatio,
            ],
            'v': [
                20 * xRatio,
            ],
            'ratio': [
                0.3,
                0.666
            ]
        }
    else:
        raise 'undefine'

def stroke_4(strokeWidth, sym):
    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']
    if sym == 'hook':
        return {
            'length': 240 * xRatio,
            'h': [
                84 * xRatio,
                32 * xRatio
            ],
            'v': [
                32 * xRatio,
                84 * xRatio,
                24 * xRatio,
                24 * xRatio,
            ],
            'ratio': [
                0.9,
                0.0
            ]
        }
    else:
        raise 'undefine'
    
def stroke_8(strokeWidth, sym):
    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']
    if sym == 'hook':
        return {
            'length': 196,
            'h': [
                24,
                28,
            ],
            'v': [
                32,
                10
            ]
        }
    elif sym == 'above':
        return {
            'length': 196,
            'h': [
                24 * xRatio,
                36 * xRatio,
                48 * xRatio
            ],
            'v': [
                12 * yRatio
            ]
        }
    else:
        raise 'undefine'
    
def dot_proto(strokeWidth):
    head = strokeWidth.x * 0.375

    comp = bs.BezierPath()
    comp.start(bs.Point(0, 0))
    comp.connect(bs.Point(head, 0))
    arc = bs.BezierCtrl.pointAndTangent(bs.Point(-1, 0), bs.Point(head, 0), bs.Point(head/2, 99), bs.Point(), 2.5, 0.5).splitting(0.5)
    comp.extend(arc[0].splitting(0.5))
    comp.extend(arc[1].splitting(0.5))
    comp.close()

    return comp

def comp_dot(ctrl, pos, strokeWidth, sym, fExtend=0, bExtend=0):
    comp = dot_proto(strokeWidth)

    if sym == '3' or sym == '1':
        if ctrl.lengthAt(1) < 128:
            sCtrl = bs.BezierCtrl(bs.Point(0, 100))
            xcenter = 0.5
        else:
            sCtrl = bs.BezierCtrl.threePointCtrl(bs.Point(), bs.Point(24, 42), bs.Point(0, 100))
            xcenter = 0.64
    else:
        raise 'undefine'
    
    tempPath = bs.BezierPath()
    tempPath.start()
    tempPath.append(sCtrl)
    sCtrl = bs.controlComp(bs.BezierCtrl(ctrl.pos), tempPath, xcenter=0, fExtend=fExtend, bExtend=bExtend)[0]
    comp = bs.controlComp(sCtrl, comp, pos, xcenter=xcenter)
    return comp, xcenter
    
def comp_rect(width):
    comp = bs.BezierPath()
    comp.start(bs.Point(0, 0))
    comp.connect(bs.Point(width, 0))
    comp.connect(bs.Point(0, 10))
    comp.connect(bs.Point(-width, 0))
    comp.connect(bs.Point(0, -10))
    comp.close()
    return comp, 0.5

def comp_6(strokeWidth, ctrl, pos):
    STROKE1 = stroke_6(strokeWidth, 'f')
    STROKE2 = stroke_6(strokeWidth, 'b')
    length = ctrl.pos.distance()
    
    comp = bs.BezierPath()
    comp.start(bs.Point(0, 0))
    comp.connect(bs.Point(STROKE1['length'] + length - STROKE2['h'][0], 0))
    comp.connect(bs.Point(STROKE2['h'][0], -STROKE2['v'][0]))
    comp.connect(bs.Point(STROKE2['h'][1], STROKE2['v'][0] + strokeWidth.y - STROKE2['v'][1]))
    comp.append(ellipticalArc(-STROKE2['h'][2], STROKE2['v'][1], False))
    comp.connect(bs.Point(STROKE1['length'] - comp.endPos().x, 0))
    comp.close()

    comp = comp.rotate(ctrl.pos.radian())
    tangent = ctrl.tangent(0)
    comp.start(pos + tangent.perpendicular() * strokeWidth.y/2 - tangent*STROKE1['length'])
    return comp

def comp_1(strokeWidth, length, sym):
    tailWidth = strokeWidth.x * .44

    comp = bs.BezierPath()
    comp.start(bs.Point(0, 0))

    if sym == 'all':
        STROKE = stroke_2(strokeWidth, 'f')
        offset = (strokeWidth.x - tailWidth) / 2

        tempCtrl = bs.BezierCtrl.pointAndTangent(bs.Point(0,1), bs.Point(), bs.Point(STROKE['h'][0] + strokeWidth.x, STROKE['v'][0]), bs.Point(strokeWidth.x, sum(STROKE['v'])), .36)
        tempCtrl = tempCtrl.splitting(tempCtrl.extermesXY()[0][0])
        comp.extend(tempCtrl)
        comp.connect(bs.Point(-offset, length - sum(STROKE['v'])))
        comp.connect(bs.Point(-tailWidth, 0))
        comp.connect(bs.Point(-offset, -length))
        comp.close()
        return comp, strokeWidth.x / 2 / (STROKE['h'][0] + strokeWidth.x)
    elif sym == 'to':
        offset = strokeWidth.x - tailWidth
        comp.connect(bs.Point(0, length))
        comp.connect(bs.Point(-tailWidth, 0))
        comp.connect(bs.Point(-offset, -length), p2=bs.Point(-offset, -length/2))

        return comp, 0.5
    elif sym == 'allTo':
        STROKE = stroke_2(strokeWidth, 'f')

        tempCtrl = bs.BezierCtrl.pointAndTangent(bs.Point(0,1), bs.Point(), bs.Point(STROKE['h'][0] + strokeWidth.x, STROKE['v'][0]), bs.Point(strokeWidth.x, sum(STROKE['v'])), .36)
        tempCtrl = tempCtrl.splitting(tempCtrl.extermesXY()[0][0])
        comp.extend(tempCtrl)
        comp.connect(bs.Point(0, length - sum(STROKE['v'])))
        comp.connect(bs.Point(-strokeWidth.x, 0))
        comp.connect(bs.Point(0, -length))
        comp.close()
        return comp, strokeWidth.x / 2 / (STROKE['h'][0] + strokeWidth.x)
    else:
        raise 'undefine'

def comp_3(strokeWidth, length, sym):
    xRatio = strokeWidth.x / STROKE_WIDTH_LIST['x']

    if sym == 'all':
        STROKE = {
            'h': [
                strokeWidth.x * .44,
                10 * xRatio
            ],
            'v': [32 * xRatio]
        }
        offset = (strokeWidth.x - STROKE['h'][0])/2
        comp = bs.BezierPath()
        comp.start(bs.Point(0, 0))
        comp.connect(bs.Point(STROKE['h'][0], 0))
        comp.connect(bs.Point(offset+STROKE['h'][1], length))
        tempPos1 = bs.Point(-strokeWidth.x-STROKE['h'][1], -STROKE['v'][0])
        tempPos2 = tempPos1 / 2 + tempPos1.perpendicular().normalization() * -STROKE['v'][0] * 0.1
        comp.append(bs.BezierCtrl.threePointCtrl(bs.Point(), tempPos2, tempPos1))
        comp.connect(bs.Point(offset, STROKE['v'][0]-length))
        comp.close()
        return comp, strokeWidth.x / 2 / (STROKE['h'][1] + strokeWidth.x)
    elif sym == 'to':
        STROKE = {
            'h': [
                12 * xRatio
            ],
            'v': [32 * xRatio]
        }
        comp = bs.BezierPath()
        comp.start(bs.Point(0, 0))
        comp.connect(bs.Point(STROKE['h'][0], length))
        tempPos1 = bs.Point(-strokeWidth.x-STROKE['h'][0], -STROKE['v'][0])
        tempPos2 = tempPos1 / 2 + tempPos1.perpendicular().normalization() * -STROKE['v'][0] * 0.1
        comp.append(bs.BezierCtrl.threePointCtrl(bs.Point(), tempPos2, tempPos1))
        comp.connect(bs.Point(0, STROKE['v'][0]-length))
        return comp, strokeWidth.x / 2 / (STROKE['h'][0] + strokeWidth.x)
    elif sym == 'bToA':
        STROKE = {
            'v': [64 * xRatio]
        }
        comp = bs.BezierPath()
        comp.start(bs.Point(0, 0))
        comp.connect(bs.Point(0, length))
        comp.connect(bs.Point(-strokeWidth.x, -STROKE['v'][0]), bs.Point(-strokeWidth.x, 0))
        comp.connect(bs.Point(0, STROKE['v'][0] - length))

        return comp, 0.5
    else:
        raise 'undefine'
