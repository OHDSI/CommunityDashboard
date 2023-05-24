import { Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabGroup, MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { Subscription, combineLatest, startWith } from 'rxjs';
import { EhdenService } from '../ehden/ehden.service';
import { renderPlot } from '../ehden/ehden-users-annually-plot';


@Component({
  selector: 'app-ehden-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './ehden-tabs.component.html',
  styleUrls: ['./ehden-tabs.component.css']
})
export class EhdenTabsComponent {
  @ViewChild('ehdenUsersAnnuallyPlot', {read: ElementRef}) ehdenUsersAnnuallyPlot!: ElementRef
  @ViewChild(MatTabGroup) tabs!: MatTabGroup


  constructor(
    private ehdenService: EhdenService
  ){}

  ngAfterViewInit(): void {
    this.ehdenServiceSubscription = combineLatest([
      this.ehdenService.valueChanges(),
      this.tabs.selectedTabChange.pipe(startWith(null))
    ]).subscribe(([es, _]) => {
      if (!es) {
        this.ehdenUsersAnnuallyPlot.nativeElement.replaceChildren(null)
        return
      }
      this.ehdenUsersAnnuallyPlot.nativeElement.replaceChildren(renderPlot(es[0]))
  })
  }

  ehdenServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.ehdenServiceSubscription?.unsubscribe()
  }
}
