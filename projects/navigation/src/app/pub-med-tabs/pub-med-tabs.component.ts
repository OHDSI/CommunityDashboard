import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { PubmedService } from '../publications/pubmed.service';
import { renderPlot } from '../publications/publications-citations-plot';
import { Subscription } from 'rxjs';


@Component({
  selector: 'app-pub-med-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './pub-med-tabs.component.html',
  styleUrls: ['./pub-med-tabs.component.css']
})
export class PubMedTabsComponent implements OnDestroy, AfterViewInit {
  @ViewChild('publicationsCitationsPlot', {read: ElementRef}) publicationsCitationsPlot!: ElementRef

  constructor(
    private pubmedService: PubmedService
  ){}

  ngAfterViewInit(): void {
    this.pubmedService.summary().subscribe(ys => 
      this.publicationsCitationsPlot.nativeElement.replaceChildren(renderPlot(ys))
    )
  }

  pubmedServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.pubmedServiceSubscription?.unsubscribe()
  }
}
