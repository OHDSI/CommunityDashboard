import { Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { YouTubeService } from '../youtube/youtube.service';
import { renderPlot } from '../youtube/youtube-annually-plot';
import { Subscription } from 'rxjs';


@Component({
  selector: 'app-you-tube-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './you-tube-tabs.component.html',
  styleUrls: ['./you-tube-tabs.component.css']
})
export class YouTubeTabsComponent {
  @ViewChild('youTubeAnnualPlot', {read: ElementRef}) youTubeAnnualPlot!: ElementRef

  constructor(
    private youTubeService: YouTubeService
  ){}

  ngAfterViewInit(): void {
    this.youTubeServiceSubscription = this.youTubeService.annually().subscribe(ys => 
      this.youTubeAnnualPlot.nativeElement.replaceChildren(renderPlot(ys))
    )
  }

  youTubeServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.youTubeServiceSubscription?.unsubscribe()
  }
}
