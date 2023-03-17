import { AfterViewInit, Component, ElementRef, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { RouterModule } from '@angular/router';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { PubmedService } from '../publications/pubmed.service';
import { Subscription } from 'rxjs';
import { renderPlot } from '../publications/publications-citations-plot';

@Component({
  selector: 'app-pub-med-summary',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './pub-med-summary.component.html',
  styleUrls: [
    './pub-med-summary.component.css',
    '../dashboard/dashboard-summary.css'
  ]
})
export class PubMedSummaryComponent implements AfterViewInit, OnDestroy {
  @ViewChild('plot', {read: ElementRef}) plot!: ElementRef

  @Input() orientation: 'horizontal' | 'vertical' = 'vertical'

  totalAuthors = this.pubmedService.totalAuthors()
  totalManuscripts = this.pubmedService.totalManuscripts()

  constructor(
    private pubmedService: PubmedService
  ){}

  ngAfterViewInit(): void {
    this.pubmedServiceSubscription = this.pubmedService.summary().subscribe(ys => 
      this.plot.nativeElement.replaceChildren(renderPlot(ys))
    )
  }

  pubmedServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.pubmedServiceSubscription?.unsubscribe()
  }
  
}
