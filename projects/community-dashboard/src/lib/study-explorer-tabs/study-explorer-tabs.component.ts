import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, ViewChildren } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatListModule } from '@angular/material/list';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import * as Plot from "@observablehq/plot";
import * as d3 from "d3"
import { debounceTime, from } from 'rxjs';
import { StudyExceptionsTableComponent } from '../study-exceptions-table/study-exceptions-table.component';
import { StudyLeadsTableComponent } from '../study-leads-table/study-leads-table.component';
import { StudyLeadsService } from '../study-leads-table/study-leads.service';
import { EXCEPTIONS } from '../study-exceptions-table/study-exceptions.service';
import { StudyPipelineService, StudyPipelineStage, StudyPromotion } from '../study-pipeline.service';
import { StudyExceptionSummariesService } from '../study-exceptions-table/study-exception-summaries.service';
import add_tooltips from '../tooltips'
import { MatInputModule } from '@angular/material/input';
import { PipelineStage, StudyPipelineSummaryService } from '../study-pipeline-summary.service';

@Component({
  selector: 'app-study-explorer-tabs',
  standalone: true,
  imports: [
    StudyExceptionsTableComponent,
    StudyLeadsTableComponent,
    MatInputModule,
    MatListModule,
    MatTabsModule,
    MatFormFieldModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './study-explorer-tabs.component.html',
  styleUrls: ['./study-explorer-tabs.component.css']
})
export class StudyExplorerTabsComponent implements AfterViewInit, OnDestroy {

  @ViewChild('studyProgress', {read: ElementRef}) studyProgress!: ElementRef
  @ViewChild('countsPlot', {read: ElementRef}) countsPlot!: ElementRef
  @ViewChild('daysPlot', {read: ElementRef}) daysPlot!: ElementRef
  @ViewChild('timelineCountsPlot', {read: ElementRef}) timelineCountsPlot!: ElementRef
  @ViewChild('studyLeadsPlot', {read: ElementRef}) studyLeadsPlot!: ElementRef
  @ViewChild('exceptionsPlot', {read: ElementRef}) exceptionsPlot!: ElementRef

  countMetrics = ['studies at stage', 'active studies at stage (last 30 days)']
  daysMetrics = ['avg. days since last update']
  studyLeadMetrics = ['active', 'completed']
  exceptionMetrics = ['count']
  studyProgressControl = new FormControl<string[]>([])
  studyProgressSearchControl = new FormControl('Covid')
  studyProgressMaxDaysControl = new FormControl(180)
  countMetricsControl = new FormControl<string[]>([...this.countMetrics])
  daysMetricsControl = new FormControl<string[]>([...this.daysMetrics])

  constructor(
    private studyLeadsService: StudyLeadsService,
    private studyExceptionSummariesService: StudyExceptionSummariesService,
    private studyPipelineService: StudyPipelineService,
    private studyPipelineSummaryService: StudyPipelineSummaryService,
  ) {}

  ngAfterViewInit(): void {
    this.renderPlots()
  }

  countMetricsControlSubscription = this.countMetricsControl.valueChanges.subscribe({
    next: _ => this.renderPlots()
  })

  studyProgressControlSubscription = this.studyProgressControl.valueChanges.subscribe({
    next: _ => this.renderPlots()
  })

  studyProgressSearchControlSubscription = this.studyProgressSearchControl.valueChanges.pipe(debounceTime(1000)).subscribe({
    next: _ => this.renderPlots()
  })

  ngOnDestroy(): void {
    this.countMetricsControlSubscription.unsubscribe()
    this.studyProgressControlSubscription.unsubscribe()
  }

  scheme(i: number) {
    return d3.schemeTableau10[i] as string
  }

  renderPlots() {

    if (this.studyProgress) {
      // from(d3.csv('https://raw.githubusercontent.com/observablehq/plot/main/test/data/bls-metro-unemployment.csv')).subscribe({
      this.studyPipelineService.find().subscribe({
        next: (data: StudyPromotion[]) => {
          if(this.studyProgress.nativeElement) {
            this.studyProgress.nativeElement?.replaceChildren(
              this._studyProgressPlot(data)
            )
          }
        }
      })
    }

    if (this.countsPlot) {
      this.studyPipelineSummaryService.find().subscribe({
        next: (stages: PipelineStage[]) => {
          if (this.countsPlot) {
            this.countsPlot.nativeElement.replaceChildren(
              this._studyPipelineSummary(stages)
            )
          }
        }
      })
    }
    
    if (this.daysPlot) {
      this.studyPipelineService.find().subscribe({
        next: stages => {
          if (this.daysPlot) {
            this.daysPlot.nativeElement.replaceChildren(
              this._barPlot(
                stages, this.daysMetricsControl.value!, 'Days', this.daysMetrics,
                [
                  'Repo Created',
                  'Started',
                  'Design Finalized',
                  'Results Available',
                ], 'stage'
              )
            )
          }
        }
      })
    }
    
    if(this.timelineCountsPlot) {
      from(d3.csv('/assets/sf-temperatures.csv')).subscribe({
        next: (sftemps: any) => {
          if(this.timelineCountsPlot.nativeElement) {
            this.timelineCountsPlot.nativeElement?.replaceChildren(
              this._timelinePlot(sftemps)
            )
          }
        }
      })
    }

    if (this.studyLeadsPlot) {
      this.studyLeadsService.find({
        filter: {
          limit: 5,
          order: ['completed desc']
        }
      }).subscribe({
        next: (studyLeads) => {
          const names = studyLeads.map(l => l.name)
          if (this.studyLeadsPlot) {
            this.studyLeadsPlot.nativeElement.replaceChildren(
              this._barXPlot(studyLeads, this.studyLeadMetrics, 'Count', this.studyLeadMetrics, names, 'name')
            )
          }
        }
      })
    }
    
    if (this.exceptionsPlot) {
      this.studyExceptionSummariesService.find().subscribe({
        next: (exceptions) => {
          if (this.exceptionsPlot) {
            for (const e of exceptions) {
              (e as any).exceptionMessage = EXCEPTIONS[e.exception]
            }
            this.exceptionsPlot.nativeElement.replaceChildren(
              this._barXPlot(exceptions, this.exceptionMetrics, 'Count', this.exceptionMetrics, Object.values(EXCEPTIONS), 'exceptionMessage')
            )
          }
        }
      })
    }
    
  }

  highlight(d: StudyPromotion) {
    const search = this.studyProgressSearchControl.value
    if (!search) { return false }
    return d.tags.join(' ').toLowerCase().includes(search.toLowerCase()) ||
      d.repoName.toLowerCase().includes(search.toLowerCase()) ||
      d.useCases.join(' ').toLowerCase().includes(search.toLowerCase()) ||
      d.studyType.join(' ').toLowerCase().includes(search.toLowerCase())
  }

  _studyProgressPlot(data: StudyPromotion[]) {
    
    const log = this.studyProgressControl.value!.includes('logScale') ? {type: 'log'} : {}
    return add_tooltips(Plot.plot({
      marginLeft: 150,
      height: 400,
      y: {
        grid: true,
        label: "Study Progress",
        domain: [
          'Complete',
          'Results Available',
          'Design Finalized',
          'Started',
          'Repo Created',
          'Invalid / Suspended',
        ]
      },
      x: {
        domain: [0, 180],
        ...log
      },
      color: {
        domain: [false, true],
        range: ["#ccc", "red"]
      },
      marks: [
        Plot.ruleY([0]),
        Plot.line(data, {
          x: "days",
          y: "stage",
          z: "repoName",
          sort: this.highlight.bind(this),
          stroke: this.highlight.bind(this),
          title: (d: StudyPromotion) => `${d.repoName}\nStudy Type:${d.studyType}\nUse Cases:${d.useCases}\nTags:${d.tags}`
        })
      ]
    }))
  }

  _studyPipelineSummary(stages: PipelineStage[]) {
    return Plot.plot({
      x: {
        type: "band",
        // tickFormat: (d: any) => d.toLocaleString("en", {month: "narrow"}),
        // label: null,
        domain: [
          'Repo Created',
          'Started',
          'Design Finalized',
          'Results Available',
          'Complete',
          'Invalid / Suspended',
        ]
      },
      color: {
        legend: true,
        // type: "linear",
        scheme: 'warm',
        domain: [
          '> 1 year',
          '< 1 year',
          '< 6 months',
          '< 90 days',
          '< 30 days',
        ]
      },
      marks: [
        Plot.barY(stages, {x: "stage", y: "count", fill: "days", title: "stage"}),
        Plot.ruleY([0])
      ]
    })
  }

  _timelinePlot(sftemps: any) {
    // For colors: https://observablehq.com/@observablehq/plot-line#cell-207
    for (const t of sftemps) {
      t['date'] = new Date(t['date'])
    }
    return Plot.plot({
      y: {
        grid: true,
        label: "Count"
      },
      marks: [
        Plot.line(sftemps, Plot.windowY({k: 14, x: "date", y: "low", stroke: "#4e79a7"})),
        Plot.line(sftemps, Plot.windowY({k: 14, x: "date", y: "high", stroke: "#e15759"})),
        Plot.ruleY([32]) // freezing
      ]
    })
  }

  _barPlot(
    stages: any, metrics: string[], measure: string, colorDomain: string[], facetDomain: string[],
    ivar: string
  ) {
    const stageMetrics = Object.assign(
      metrics.flatMap(
        (metric: any) => stages.map((d: any) => {
          const flat: any = {
            metric
          }
          flat[ivar] = d[ivar]
          flat[measure] = d[metric]
          return flat
        })
      ), {metrics}
    )
    return Plot.plot({
      x: {
        axis: null,
        domain: stageMetrics.metrics
      },
      y: {
        grid: true,
        tickFormat: "s"
      },
      color: {
        domain: colorDomain,
        scheme: metrics.length ? "tableau10" : undefined
      },
      fx: {
        domain: facetDomain,
        label: null,
        tickSize: 6
      },
      facet: {
        data: stageMetrics,
        x: ivar
      },
      marks: [
        Plot.barY(stageMetrics, {x: "metric", y: measure, fill: "metric", title: "metric"}),
        Plot.ruleY([0])
      ]
    })
  }

  _barXPlot(
    stages: any, metrics: string[], measure: string, colorDomain: string[], 
    facetDomain: string[], 
    ivar: string
  ) {
    const stageMetrics = Object.assign(
      metrics.flatMap(
        (metric: any) => stages.map((d: any) => {
          const flat: any = {
            metric
          }
          flat[ivar] = d[ivar]
          flat[measure] = d[metric]
          return flat
        })
      ), {metrics}
    )
    return Plot.plot({
      y: {
        axis: null,
        domain: stageMetrics.metrics,
      },
      x: {
        grid: true,
        tickFormat: "s"
      },
      color: {
        domain: colorDomain,
        scheme: metrics.length ? "tableau10" : undefined
      },
      fy: {
        domain: facetDomain,
        label: null,
        tickSize: 6,
      },
      facet: {
        marginLeft: 200,
        data: stageMetrics,
        y: ivar
      },
      marks: [
        Plot.barX(stageMetrics, {y: "metric", x: measure, fill: "metric", title: "metric"}),
        Plot.ruleX([0])
      ]
    })
  }
}