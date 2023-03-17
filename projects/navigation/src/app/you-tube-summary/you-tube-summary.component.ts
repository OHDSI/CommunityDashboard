import { Component, ElementRef, Input, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { YouTubeServiceWithCountsSummary } from '../youtube/youtube.service';
import { renderPlot } from '../youtube/youtube-annually-plot';
import { Subscription } from 'rxjs/internal/Subscription';
import { map } from 'rxjs';

@Component({
  selector: 'app-you-tube-summary',
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
  templateUrl: './you-tube-summary.component.html',
  styleUrls: [
    './you-tube-summary.component.css',
    '../dashboard/dashboard-summary.css',
  ]
})
export class YouTubeSummaryComponent {
  @ViewChild('plot', {read: ElementRef}) plot!: ElementRef

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'

  hoursWatched = this.youTubeService.hoursWatched().pipe(
    map(h => {
      return `${Math.floor(h / 1000)}K+`
    })
  )
  videosPublished = this.youTubeService.videosPublished()

  constructor(
    private youTubeService: YouTubeServiceWithCountsSummary
  ){}

  ngAfterViewInit(): void {
    const PLOT_HEIGHT = 300
    this.youTubeServiceSubscription = this.youTubeService.annually().subscribe(ys => 
      this.plot.nativeElement.replaceChildren(renderPlot(ys, PLOT_HEIGHT))
    )
  }

  youTubeServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.youTubeServiceSubscription?.unsubscribe()
  }
}
