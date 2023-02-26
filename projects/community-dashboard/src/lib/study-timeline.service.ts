import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestMemory, RestToken } from '@community-dashboard/rest';
import { map } from 'rxjs';
import { ScanLogsService } from './scan-logs.service';

interface TimelineDay {
  date: string,
  updatesLast30: number,
  activeStudiesLast30: number,
  newStudiesLast30: number,
  studiesStartedLast30: number,
  designFinalizedLast30: number,
  resultsAvailableLast30: number,
  studiesCompletedLast30: number,
}

@Injectable({
  providedIn: 'root'
})
export class StudyTimelineService extends RestDelegate<TimelineDay> {

  constructor(
    scanLogsService: ScanLogsService,
  ) { 
    const rest = new RestMemory(scanLogsService.cache.pipe(
      map(ls => {
        const vs: {[key: string]: {
          updates: number,
          activeStudies: number,
          newStudies: number,
          studiesStarted: number,
          designFinalized: number,
          resultsAvailable: number,
          studiesCompleted: number,
        }} = {}
        const lastStatuses: {[key: string]: string} = {}
        for (const l of ls) {
          if (!l.readmeCommit?.author?.date) {
            continue
          }
          const dateKey = new Date(l.readmeCommit?.author?.date).toISOString().slice(0,10)
          if (!(dateKey in vs)) {
            vs[dateKey] = {
              updates: 0,
              activeStudies: 0,
              newStudies: 0,
              studiesStarted: 0,
              designFinalized: 0,
              resultsAvailable: 0,
              studiesCompleted: 0,
            }
          }
          vs[dateKey].updates += 1
          const newStatus: string | null | undefined = (l.repository?.name && (lastStatuses[l.repository?.name] != l.readmeCommit.summary?.status)) ? l.readmeCommit.summary?.status : null
          if (newStatus && [
            'Repo Created',
            'Started',
            'Design Finalized',
            'Results Available',
          ].includes(newStatus)) {
            vs[dateKey].activeStudies += 1
          }
          if (newStatus === 'Repo Created') {
            vs[dateKey].newStudies += 1
          }
          if (newStatus === 'Started') {
            vs[dateKey].studiesStarted += 1
          }
          if (newStatus === 'Design Finalized') {
            vs[dateKey].designFinalized += 1
          }
          if (newStatus === 'Results Available') {
            vs[dateKey].resultsAvailable += 1
          }
          if (newStatus === 'Completed') {
            vs[dateKey].studiesCompleted += 1
          }
        }
        const commitDates = Object.keys(vs).sort()
        const timelineX = getDaysArray(commitDates[0], commitDates[commitDates.length - 1]).map(d => d.toISOString().slice(0,10))
        for (const d of timelineX) {
          if (!(d in vs)) {
            vs[d] = {
              updates: 0,
              activeStudies: 0,
              newStudies: 0,
              studiesStarted: 0,
              designFinalized: 0,
              resultsAvailable: 0,
              studiesCompleted: 0,
            }
          }
        }
        const updatesLast30 = movingAverage(timelineX.map(d => vs[d].updates), 30)
        const activeStudiesLast30 = movingAverage(timelineX.map(d => vs[d].activeStudies), 30)
        const newStudiesLast30 = movingAverage(timelineX.map(d => vs[d].newStudies), 30)
        const studiesStartedLast30 = movingAverage(timelineX.map(d => vs[d].studiesStarted), 30)
        const designFinalizedLast30 = movingAverage(timelineX.map(d => vs[d].designFinalized), 30)
        const resultsAvailableLast30 = movingAverage(timelineX.map(d => vs[d].resultsAvailable), 30)
        const studiesCompletedLast30 = movingAverage(timelineX.map(d => vs[d].studiesCompleted), 30)
        return timelineX.map((d, i) => ({
          date: d,
          updatesLast30: updatesLast30[i],
          activeStudiesLast30: activeStudiesLast30[i],
          newStudiesLast30: newStudiesLast30[i],
          studiesStartedLast30: studiesStartedLast30[i],
          designFinalizedLast30: designFinalizedLast30[i],
          resultsAvailableLast30: resultsAvailableLast30[i],
          studiesCompletedLast30: studiesCompletedLast30[i],
        })).reduce((acc, d) => {
          acc[d.date] = d
          return acc
        }, {} as {[key: string]: TimelineDay})
      }),
      map(tl => {
        return {
          '/study-timeline': tl
        }
      })
    ))
    super(rest, '', 'study-timeline')
  }
}

// https://stackoverflow.com/questions/4413590/javascript-get-array-of-dates-between-2-dates
var getDaysArray = function(start: string, end: string) {
  for(var arr=[],dt=new Date(start); dt<=new Date(end); dt.setDate(dt.getDate()+1)){
      arr.push(new Date(dt));
  }
  return arr;
};

// https://observablehq.com/@d3/moving-average
function movingAverage(values: number[], N: number) {
  let i = 0;
  let sum = 0;
  const means = new Float64Array(values.length).fill(NaN);
  for (let n = Math.min(N - 1, values.length); i < n; ++i) {
    sum += values[i];
  }
  for (let n = values.length; i < n; ++i) {
    sum += values[i];
    means[i] = sum / N;
    sum -= values[i - N + 1];
  }
  return means;
}
