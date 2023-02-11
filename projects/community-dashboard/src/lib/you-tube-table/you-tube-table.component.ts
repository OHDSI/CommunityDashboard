import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, ViewChild } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { TableDataSourceOld } from '../table-data-source-old';
import { YouTubeVideo, YouTubeService } from './you-tube.service';

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
  @ViewChild(MatTable) table!: MatTable<YouTubeVideo>;
  dataSource: TableDataSourceOld<YouTubeVideo>;

  @Input()
  displayedColumns!: string[]

  constructor(
    public youTubeService: YouTubeService,
  ) {
    this.dataSource = new TableDataSourceOld(youTubeService);
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }
}
