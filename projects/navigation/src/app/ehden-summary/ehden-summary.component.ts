import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { EhdenService } from '../ehden/ehden.service';
import { renderPlot } from '../ehden/ehden-users-annually-plot';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-ehden-summary',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './ehden-summary.component.html',
  styleUrls: [
    './ehden-summary.component.css',
    '../dashboard/dashboard-summary.css',
  ]
})
export class EhdenSummaryComponent {
  @ViewChild('plot', {read: ElementRef}) plot!: ElementRef

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'

  courseCount = this.ehdenService.courseCount()
  completionCount = this.ehdenService.courseCompletions()

  constructor(
    private ehdenService: EhdenService
  ){}

  ngAfterViewInit(): void {
    this.ehdenServiceSubscription = this.ehdenService.valueChanges().subscribe(es => {
      if (!es) {
        this.plot.nativeElement.replaceChildren(null)
        return
      }
      const PLOT_HEIGHT = 300
      this.plot.nativeElement.replaceChildren(renderPlot(es[0], PLOT_HEIGHT))
    })
  }

  ehdenServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.ehdenServiceSubscription?.unsubscribe()
  }
  
}
