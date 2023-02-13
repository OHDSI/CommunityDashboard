import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FundingTableComponent } from './funding-table.component';

describe('FundingTableComponent', () => {
  let component: FundingTableComponent;
  let fixture: ComponentFixture<FundingTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ FundingTableComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FundingTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
