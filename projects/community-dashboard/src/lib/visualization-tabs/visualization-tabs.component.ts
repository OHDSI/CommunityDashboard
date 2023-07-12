import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule, MatTabGroup } from '@angular/material/tabs'; 
import { MatIconModule } from '@angular/material/icon'; 
import { MatButtonModule } from '@angular/material/button'; 
import { ViewChild } from '@angular/core';
import { AfterViewInit } from '@angular/core';
import { BehaviorSubject, Subscription, map } from 'rxjs';
import { OnDestroy } from '@angular/core';

@Component({
  selector: 'lib-visualization-tabs',
  standalone: true,
  imports: [
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './visualization-tabs.component.html',
  styleUrls: ['./visualization-tabs.component.css']
})
export class VisualizationTabsComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatTabGroup) tabGroup?: MatTabGroup
  
  firstTab = new BehaviorSubject(true)
  lastTab = new BehaviorSubject(false)
  
  ngAfterViewInit(): void {
    this.subscriptions.push(
      this.tabGroup!.selectedIndexChange.subscribe(
        i => {
          if (i === 0) {
            this.firstTab.next(true)
            this.lastTab.next(false)
          } else if (i === 2) {
            this.firstTab.next(false)
            this.lastTab.next(true)
          } else {
            this.firstTab.next(false)
            this.lastTab.next(false)
          }
        }
      )
    )
  }
    
  subscriptions: Subscription[] = []
  
  ngOnDestroy(): void {
    for (const s of this.subscriptions) {
      s.unsubscribe()
    }
  }

  nextTab() {
    if (this.tabGroup) {
      this.tabGroup.selectedIndex = this.tabGroup.selectedIndex! + 1
    }
  }

  previousTab() {
    if (this.tabGroup) {
      this.tabGroup.selectedIndex = this.tabGroup.selectedIndex! - 1
    }
  }
}
