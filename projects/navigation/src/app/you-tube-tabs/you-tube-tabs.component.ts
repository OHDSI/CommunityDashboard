import { Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabGroup, MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { YouTubeServiceWithCountsSummary } from '../youtube/youtube.service';
import { renderPlot } from '../youtube/youtube-annually-plot';
import { Subscription, combineLatest, startWith } from 'rxjs';


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
  @ViewChild(MatTabGroup) tabs!: MatTabGroup


  constructor(
    private youTubeService: YouTubeServiceWithCountsSummary
  ){}

  ngAfterViewInit(): void {
    this.youTubeServiceSubscription = combineLatest([
      this.youTubeService.annually(),
      this.tabs.selectedTabChange.pipe(startWith(null))
    ]).subscribe(([ys, _]) => 
      this.youTubeAnnualPlot.nativeElement.replaceChildren(renderPlot(ys))
    )
  }

  youTubeServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.youTubeServiceSubscription?.unsubscribe()
  }
}
