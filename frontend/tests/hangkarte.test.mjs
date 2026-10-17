import test from 'node:test'
import assert from 'node:assert/strict'
import {formatShare, distanceM, pointProblem, shareColor, driverLabel, landCoverLabel, CAVEATS, MAX_POINTS} from '../src/hangkarte.js'

test('shares are shown as German percentages and invalid values are rejected',()=>{
  assert.equal(formatShare(0.3),'30,0 %')
  assert.equal(formatShare(0.7361),'73,6 %')
  assert.equal(formatShare(0.00002),'< 0,1 %')
  for(const bad of [NaN,-0.1,1.2,undefined]) assert.equal(formatShare(bad),'–')
  assert.equal(formatShare(1),'100,0 %')
})
test('distance uses the great circle, not degrees',()=>{
  const a={longitude:10.5617,latitude:47.1478}
  assert.ok(Math.abs(distanceM(a,{longitude:10.5617,latitude:47.1478+0.01})-1111.9)<3)           // 0.01 deg latitude
  const lon=distanceM(a,{longitude:10.5617+0.01,latitude:47.1478})                               // a degree of longitude is shorter at 47 deg N
  assert.ok(lon>740&&lon<790)
  assert.equal(distanceM(a,a),0)
})
test('custom points must be inside the area, distinct and limited',()=>{
  const c={longitude:10.56,latitude:47.15}
  assert.equal(pointProblem({longitude:10.561,latitude:47.151},c,1500,[]),'')
  assert.match(pointProblem({longitude:10.7,latitude:47.15},c,1500,[]),/außerhalb/)
  assert.match(pointProblem({longitude:10.561,latitude:47.151},c,1500,[{longitude:10.561,latitude:47.151}]),/schon gewählt/)
  assert.match(pointProblem({longitude:10.561,latitude:47.151},null,1500,[]),/Gebiet wählen/)
  const many=Array.from({length:MAX_POINTS},(_,i)=>({longitude:10.56+i*0.0005,latitude:47.15}))
  assert.match(pointProblem({longitude:10.5605,latitude:47.152},c,1500,many),/Höchstens/)
})
test('colour scale is monotone in brightness and clamps out-of-range input',()=>{
  const lum=s=>{const [r,g,b]=shareColor(s).match(/\d+/g).map(Number);return .2126*r+.7152*g+.0722*b}
  const values=[0,.01,.1,.3,.6,1]
  for(let i=1;i<values.length;i++) assert.ok(lum(values[i])>lum(values[i-1]))
  assert.equal(shareColor(5),shareColor(1)); assert.equal(shareColor(-1),shareColor(0))
})
test('labels exist for every model feature class and unknown names pass through',()=>{
  assert.equal(driverLabel('slope'),'Neigung'); assert.equal(driverLabel('unbekannt'),'unbekannt')
  assert.equal(landCoverLabel('lc_forest'),'Wald'); assert.equal(landCoverLabel(null),'–')
})
test('honesty statements stay in the page: not a probability, not a warning, reporting bias, no causality',()=>{
  const text=CAVEATS.join(' ')
  for(const needle of ['keine Eintrittswahrscheinlichkeit','keine Warnung','Meldebias','verursacht','0,85','0,70']) assert.ok(text.includes(needle),needle)
})
