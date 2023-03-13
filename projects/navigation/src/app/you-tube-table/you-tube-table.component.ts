import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSource  } from '@community-dashboard/rest';
import { YouTube, YouTubeService } from '../youtube/youtube.service';
import * as d3 from 'd3'

@Component({
  selector: 'app-you-tube-table',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    CommonModule
  ],
  templateUrl: './you-tube-table.component.html',
  styleUrls: ['./you-tube-table.component.css']
})
export class YouTubeTableComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<YouTube>;
  dataSource: TableDataSource<YouTube>;

  @Input()
  displayedColumns!: string[]

  constructor(
    public youTubeService: YouTubeService,
  ) {
    this.dataSource = new TableDataSource(youTubeService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  latestViewCount(y: YouTube) {
    return y.counts.sort((a, b) => d3.descending(a.checkedOn, b.checkedOn))[0]['viewCount']
  }
}
