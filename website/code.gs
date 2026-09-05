// ===========================
// 상수
// ===========================

const LANG = {
  KO: "ko"
};

const SHEETS = {
  MENU: "메뉴판",
  PRICE: "메뉴판",
  NOTICE: "안내"
};

const CACHE_EXPIRATION = 21600;        // 캐시Service TTL (6시간)
const CACHE_REFRESH_TIME = 21000000;   // 강제 재생성 기준 (5시간 50분)
const CACHE_SIZE_LIMIT = 90000;        // 90KB

const PROP_LAST_EDIT = "last_sheet_edit";
const PROP_CACHE_ERROR = "last_cache_error";
const PROP_GOOGLE_APPS_SECRET = "google_apps_secret";

// 이미지 업데이트 결과 저장
const PROP_IMAGE_UPDATE_PREFIX = "image_update_";
const IMAGE_UPDATE_STATUS_EXPIRATION = 600; // 10분

const IMAGE_ADDRESS_COLUMN = "사진";
const PRICE_HEADER_SEARCH_ROWS = 10;   // PRICE 헤더 검색 최대 행 수

// ===========================
// 공백 데이터 판정
// ===========================

function hasVisibleText(value) {

  return String(value || "")
    .replace(/[\s\u00A0\u2000-\u200D\u202F\u205F\u3000\u3164\uFEFF]/g, "")
    !== "";

}

// ===========================
// 시트 데이터
// ===========================

function getSheetData(spreadsheet, sheetName) {

  const sheet =
    spreadsheet.getSheetByName(sheetName);

  if (!sheet) {
    return [];
  }

  const values =
    sheet.getDataRange().getValues();

  if (values.length <= 1) {
    return [];
  }

  const headers =
    values.shift()
      .map(header =>
        String(header)
          .replace(/\t/g, "")
          .trim()
      );

  const itemIndex =
    headers.indexOf("항목");

  return values
    .filter(row => {

      // '항목' 열이 있는 시트만 적용
      if (itemIndex === -1) {
        return true;
      }

      // '항목'이 비어 있는 행은 제외
      return hasVisibleText(
        row[itemIndex]
      );

    })
    .map(row => {

      const obj = {};

      headers.forEach(
        (header, index) => {

          obj[header] =
            row[index];

        }
      );

      return obj;

    });

}

// ===========================
// 초기 설정
// ===========================

function setGoogleAppsSecret() {

  PropertiesService
    .getScriptProperties()
    .setProperty(
      PROP_GOOGLE_APPS_SECRET,
      "CHANGE_ME"
    );

  console.log(
    "google_apps_secret saved"
  );

}

function checkGoogleAppsSecret() {

  const value =
    PropertiesService
      .getScriptProperties()
      .getProperty(
        PROP_GOOGLE_APPS_SECRET
      );

  console.log(
    value
      ? "google_apps_secret configured"
      : "google_apps_secret missing"
  );

}

// ===========================
// 이미지 업데이트
// ===========================

function jsonResponse(payload) {

  return ContentService
    .createTextOutput(
      JSON.stringify(payload)
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );

}

function getHeaderIndex(headers, name) {

  return headers.indexOf(name);

}

function ensureColumn(
  sheet,
  headers,
  name
) {

  const index =
    getHeaderIndex(
      headers,
      name
    );

  if (index !== -1) {
    return index;
  }

  const nextColumn =
    headers.length + 1;

  sheet
    .getRange(
      1,
      nextColumn
    )
    .setValue(name);

  headers.push(name);

  return headers.length - 1;

}

function normalizeMenuKeyValue(value) {
  const text = String(value || "").trim();

  return hasVisibleText(text)
    ? text
    : "";
}


function buildMenuRowKey(category, name) {
  return [
    normalizeMenuKeyValue(category),
    normalizeMenuKeyValue(name)
  ].join("\u0001");
}

// ===========================
// PRICE 헤더 행 찾기
// ===========================

function findPriceHeaderRow(
  values
) {

  for (
    let rowIndex = 0;
    rowIndex < values.length;
    rowIndex += 1
  ) {

    const headers =
      values[rowIndex]
        .map(header =>
          String(header)
            .replace(/\t/g, "")
            .trim()
        );

    const hasCategory =
      headers.includes("항목");

    const hasName =
      headers.includes("이름");

    if (
      hasCategory &&
      hasName
    ) {
      return rowIndex;
    }

  }

  return -1;

}

// ===========================
// Update Price Sheet Images
// ===========================

function updateMenuImages(payload) {

  const expectedSecret =
    PropertiesService
      .getScriptProperties()
      .getProperty(
        PROP_GOOGLE_APPS_SECRET
      );

  if (!expectedSecret) {

    return {
      ok: false,
      error:
        "Google Apps secret is not configured"
    };

  }

  if (
    payload.googleAppsSecret !==
    expectedSecret
  ) {

    return {
      ok: false,
      error:
        "Unauthorized"
    };

  }

  const requestId =
    String(
      payload.requestId || ""
    ).trim();

  if (!requestId) {

    return {
      ok: false,
      error:
        "requestId is required"
    };

  }

  const rows =
    Array.isArray(payload.rows)
      ? payload.rows
      : [];



  // ===========================
  // 스프레드시트 로드
  // ===========================
  const spreadsheet =
    SpreadsheetApp
      .getActiveSpreadsheet();

  const sheet =
    spreadsheet
      .getSheetByName(
        SHEETS.PRICE
      );

  if (!sheet) {

    return {
      ok: false,
      error:
        `Sheet not found: ${SHEETS.PRICE}`
    };

  }

  const lastRow =
    sheet.getLastRow();

  const lastColumn =
    sheet.getLastColumn();

  if (
    lastRow === 0 ||
    lastColumn === 0
  ) {

    return {
      ok: false,
      error:
        `${SHEETS.PRICE} sheet has no data`
    };

  }


  // ===========================
  // 헤더 검색
  // ===========================
  const headerSearchRowCount =
    Math.min(
      PRICE_HEADER_SEARCH_ROWS,
      lastRow
    );

  const headerSearchValues =
    sheet
      .getRange(
        1,
        1,
        headerSearchRowCount,
        lastColumn
      )
      .getValues();

  const headerRowIndex =
    findPriceHeaderRow(
      headerSearchValues
    );

  if (headerRowIndex === -1) {

    return {
      ok: false,
      error:
        `${SHEETS.PRICE} sheet requires header row`
    };

  }

  const headers =
    headerSearchValues[
      headerRowIndex
    ]
      .map(header =>
        String(header)
          .replace(/\t/g, "")
          .trim()
      );


  const categoryIndex =
    getHeaderIndex(
      headers,
      "항목"
    );

  const nameIndex =
    getHeaderIndex(
      headers,
      "이름"
    );


  if (
    categoryIndex === -1 ||
    nameIndex === -1
  ) {

    return {
      ok: false,
      error:
        "Required columns are missing"
    };

  }


  // ===========================
  // 이미지 컬럼 처리
  // ===========================
  const imageIndex =
    ensureColumn(
      sheet,
      headers,
      payload.imageColumn ||
        IMAGE_ADDRESS_COLUMN
    );


  const dataStartRow =
    headerRowIndex + 2;

  const dataRowCount =
    lastRow -
    headerRowIndex -
    1;


  if (dataRowCount <= 0) {

    return {
      ok: false,
      error:
        `${SHEETS.PRICE} sheet has no menu rows`
    };

  }


  // ===========================
  // 필요한 데이터만 한 번에 읽기
  //
  // 항목/이름/사진이 떨어져 있어도
  // 하나의 연속 범위로 읽는다.
  // 불필요한 전체 시트 읽기를 피하면서
  // Spreadsheet 서비스 호출 횟수를 줄인다.
  // ===========================
  const dataStartColumn =
    Math.min(
      categoryIndex,
      nameIndex,
      imageIndex
    );

  const dataEndColumn =
    Math.max(
      categoryIndex,
      nameIndex,
      imageIndex
    );

  const dataColumnCount =
    dataEndColumn -
    dataStartColumn +
    1;

  const dataValues =
    sheet
      .getRange(
        dataStartRow,
        dataStartColumn + 1,
        dataRowCount,
        dataColumnCount
      )
      .getValues();


  // ===========================
  // 메뉴 인덱스 생성
  // ===========================
  const rowByKey = {};

  const categoryOffset =
    categoryIndex -
    dataStartColumn;

  const nameOffset =
    nameIndex -
    dataStartColumn;

  const imageOffset =
    imageIndex -
    dataStartColumn;

  for (
    let index = 0;
    index < dataValues.length;
    index += 1
  ) {

    const category =
      dataValues[index][categoryOffset];

    const name =
      dataValues[index][nameOffset];

    if (
      !hasVisibleText(category) &&
      !hasVisibleText(name)
    ) {
      continue;
    }

    const key =
      buildMenuRowKey(
        category,
        name
      );

    rowByKey[key] =
      index;

  }


  let updated = 0;
  let skipped = 0;

  // 변경된 행 인덱스
  const changedRows =
    new Set();


  // ===========================
  // 메모리에서 변경 적용
  // ===========================
  rows.forEach(
    item => {

      const key =
        buildMenuRowKey(
          item.category,
          item.name
        );

      const rowIndex =
        rowByKey[key];

      const destination =
        String(
          item.destination || ""
        ).trim();

      if (
        rowIndex === undefined ||
        !hasVisibleText(destination)
      ) {
        skipped += 1;
        return;
      }

      const currentValue =
        String(
          dataValues[rowIndex][imageOffset]
        ).trim();


      if (
        currentValue ===
        destination
      ) {

        skipped += 1;

        return;

      }


      dataValues[rowIndex][imageOffset] =
        destination;

      changedRows.add(
        rowIndex
      );

      updated += 1;

    }
  );



  // ===========================
  // 변경된 이미지 셀만 저장
  //
  // 연속된 행은 하나의 setValues()
  // 호출로 묶는다.
  // ===========================
  if (updated > 0) {

    const sortedRows =
      Array.from(
        changedRows
      ).sort(
        (a, b) => a - b
      );


    let startIndex =
      sortedRows[0];

    let endIndex =
      sortedRows[0];


    const writeRange = (
      start,
      end
    ) => {

      const valuesToWrite =
        dataValues
          .slice(
            start,
            end + 1
          )
          .map(
            row => [
              row[imageOffset]
            ]
          );


      sheet
        .getRange(
          dataStartRow + start,
          imageIndex + 1,
          end - start + 1,
          1
        )
        .setValues(
          valuesToWrite
        );

    };


    for (
      let index = 1;
      index < sortedRows.length;
      index += 1
    ) {

      const rowIndex =
        sortedRows[index];


      if (
        rowIndex ===
        endIndex + 1
      ) {

        endIndex =
          rowIndex;

        continue;

      }


      writeRange(
        startIndex,
        endIndex
      );


      startIndex =
        rowIndex;

      endIndex =
        rowIndex;

    }


    writeRange(
      startIndex,
      endIndex
    );

  }


  // ===========================
  // 캐시 Invalidate
  // ===========================
  if (updated > 0) {

    PropertiesService
      .getScriptProperties()
      .setProperty(
        PROP_LAST_EDIT,
        Date.now().toString()
      );

    getCacheStore()
      .remove(
        `cache_${LANG.KO}`
      );

  }


  // ===========================
  // 결과 저장
  // ===========================
  const result = {

    ok: true,

    requestId:
      requestId,

    updated:
      updated,

    skipped:
      skipped,

    createdAt:
      Date.now()

  };


  PropertiesService
    .getScriptProperties()
    .setProperty(
      PROP_IMAGE_UPDATE_PREFIX +
        requestId,
      JSON.stringify(result)
    );

  return result;

}

// ===========================
// 이미지 업데이트 Status
// ===========================

function getImageUpdateStatus(
  requestId
) {

  requestId =
    String(
      requestId || ""
    ).trim();

  if (!requestId) {

    return {
      ok: false,
      error:
        "requestId is required"
    };

  }

  const key =
    PROP_IMAGE_UPDATE_PREFIX +
    requestId;

  const properties =
    PropertiesService
      .getScriptProperties();

  const value =
    properties.getProperty(
      key
    );

  // ==================================
  // 아직 결과가 저장되지 않은 경우
  // ==================================

  if (!value) {

    return {

      ok: false,

      pending: true,

      requestId:
        requestId,

      error:
        "Update result is not available yet"

    };

  }

  let result;

  try {

    result =
      JSON.parse(value);

  } catch (error) {

    // 손상된 결과만 삭제
    properties.deleteProperty(
      key
    );

    return {

      ok: false,

      error:
        "Invalid stored update result"

    };

  }

  // ==================================
  // 결과 만료 확인
  //
  // 기존 결과에는 createdAt이 있으므로
  // 기존 저장 데이터도 그대로 호환
  // ==================================

  const createdAt =
    Number(
      result.createdAt
    ) || 0;

  const expired =
    createdAt > 0 &&
    Date.now() - createdAt >
      IMAGE_UPDATE_STATUS_EXPIRATION * 1000;

  if (expired) {

    properties.deleteProperty(
      key
    );

    return {

      ok: false,

      pending: true,

      requestId:
        requestId,

      error:
        "Update result has expired"

    };

  }

  // ==================================
  // 정상적으로 결과 확인
  //
  // 현재 요청 결과만 삭제
  // ==================================

  properties.deleteProperty(
    key
  );

  // 오래된 image_update_* 결과 정리
  const now = Date.now();

  const expiration =
    IMAGE_UPDATE_STATUS_EXPIRATION * 1000;

  const allProperties =
    properties.getProperties();

  Object.keys(
    allProperties
  ).forEach(
    propertyKey => {

      if (
        !propertyKey.startsWith(
          PROP_IMAGE_UPDATE_PREFIX
        )
      ) {

        return;

      }

      try {

        const stored =
          JSON.parse(
            allProperties[propertyKey]
          );

        if (
          stored.createdAt &&
          now - stored.createdAt >
            expiration
        ) {

          properties.deleteProperty(
            propertyKey
          );

        }

      } catch (e) {

        properties.deleteProperty(
          propertyKey
        );

      }

    }
  );

  return result;

}

// ===========================
// 캐시
// ===========================

function getCacheStore() {

  return CacheService
    .getScriptCache();

}

function saveCacheError(
  message
) {

  PropertiesService
    .getScriptProperties()
    .setProperty(
      PROP_CACHE_ERROR,
      `${new Date().toISOString()} ${message}`
    );

}

function checkCacheError() {

  const error =
    PropertiesService
      .getScriptProperties()
      .getProperty(
        PROP_CACHE_ERROR
      );

  console.log(
    error || "No cache error"
  );

}

function checkCacheStatus() {

  const props =
    PropertiesService
      .getScriptProperties();

  const lastSheetEdit =
    Number(
      props.getProperty(
        PROP_LAST_EDIT
      )
    ) || 0;

  const cache =
    getCacheStore()
      .get(
        `cache_${LANG.KO}`
      );

  if (!cache) {

    console.log(
      "Cache: 없음"
    );

    return;

  }

  const cached =
    JSON.parse(cache);

  const age =
    Date.now() -
    cached.createdAt;

  const expired =
    age >=
    CACHE_REFRESH_TIME;

  console.log(
    "Sheet last edit:",
    new Date(
      lastSheetEdit
    )
  );

  console.log(
    "Cache created:",
    new Date(
      cached.createdAt
    )
  );

  console.log(
    "Cache sheet version:",
    new Date(
      cached.sheetUpdatedAt
    )
  );

  console.log(
    "Cache age:",
    Math.floor(
      age / 1000
    ),
    "seconds"
  );

  console.log(
    "Cache expired:",
    expired
  );

  console.log(
    "Cache valid:",
    cached.sheetUpdatedAt ===
      lastSheetEdit &&
    !expired
  );

}

function getLastSheetEdit() {

  return Number(
    PropertiesService
      .getScriptProperties()
      .getProperty(
        PROP_LAST_EDIT
      )
  ) || 0;

}

function getCachedResponse(
  lang
) {

  const cache =
    getCacheStore();

  const json =
    cache.get(
      `cache_${lang}`
    );

  if (!json) {
    return null;
  }

  const cached =
    JSON.parse(json);

  const lastEdit =
    getLastSheetEdit();

  const expired =
    Date.now() -
      cached.createdAt >=
    CACHE_REFRESH_TIME;

  if (
    cached.sheetUpdatedAt !==
      lastEdit ||
    expired
  ) {

    return null;

  }

  return JSON.stringify({

    lang:
      lang,

    ...cached.data

  });

}

function setCachedResponse(
  lang,
  data
) {

  const payload = {

    createdAt:
      Date.now(),

    sheetUpdatedAt:
      getLastSheetEdit(),

    data:
      data

  };

  const json =
    JSON.stringify(
      payload
    );

  const size =
    Utilities
      .newBlob(json)
      .getBytes()
      .length;

  if (
    size >
    CACHE_SIZE_LIMIT
  ) {

    saveCacheError(
      `Cache too large: cache_${lang} (${size} bytes)`
    );

    return false;

  }

  try {

    getCacheStore()
      .put(
        `cache_${lang}`,
        json,
        CACHE_EXPIRATION
      );

    return true;

  } catch (error) {

    saveCacheError(
      `Cache write failed: ${error.message}`
    );

    return false;

  }

}

// ===========================
// 이미지 프로세서용 빈 항목 행
// ===========================

function getImageProcessorBlankPriceRows(
  spreadsheet
) {

  const sheet =
    spreadsheet.getSheetByName(
      SHEETS.PRICE
    );

  if (!sheet) {
    return [];
  }

  const lastRow =
    sheet.getLastRow();

  const lastColumn =
    sheet.getLastColumn();

  if (
    lastRow === 0 ||
    lastColumn === 0
  ) {
    return [];
  }

  const headerSearchRowCount =
    Math.min(
      PRICE_HEADER_SEARCH_ROWS,
      lastRow
    );

  const headerSearchValues =
    sheet
      .getRange(
        1,
        1,
        headerSearchRowCount,
        lastColumn
      )
      .getValues();

  const headerRowIndex =
    findPriceHeaderRow(
      headerSearchValues
    );

  if (headerRowIndex === -1) {
    return [];
  }

  const headers =
    headerSearchValues[
      headerRowIndex
    ]
      .map(header =>
        String(header)
          .replace(/\t/g, "")
          .trim()
      );

  const categoryIndex =
    headers.indexOf("항목");

  const nameIndex =
    headers.indexOf("이름");

  const imageIndex =
    headers.indexOf(IMAGE_ADDRESS_COLUMN);

  if (
    categoryIndex === -1 ||
    nameIndex === -1 ||
    imageIndex === -1
  ) {
    return [];
  }

  const dataStartRow =
    headerRowIndex + 2;

  const dataRowCount =
    lastRow -
    headerRowIndex -
    1;

  if (dataRowCount <= 0) {
    return [];
  }

  const dataStartColumn =
    Math.min(
      categoryIndex,
      nameIndex,
      imageIndex
    );

  const dataEndColumn =
    Math.max(
      categoryIndex,
      nameIndex,
      imageIndex
    );

  const dataValues =
    sheet
      .getRange(
        dataStartRow,
        dataStartColumn + 1,
        dataRowCount,
        dataEndColumn - dataStartColumn + 1
      )
      .getValues();

  const categoryOffset =
    categoryIndex - dataStartColumn;

  const nameOffset =
    nameIndex - dataStartColumn;

  const imageOffset =
    imageIndex - dataStartColumn;

  const rows = [];

  dataValues.forEach(
    row => {

      if (
        hasVisibleText(
          row[categoryOffset]
        ) ||
        !hasVisibleText(
          row[nameOffset]
        )
      ) {
        return;
      }

      rows.push({
        항목: row[categoryOffset],
        이름: row[nameOffset],
        [IMAGE_ADDRESS_COLUMN]: row[imageOffset]
      });

    }
  );

  return rows;

}

function getImageProcessorResponseJson(
  lang
) {

  const spreadsheet =
    SpreadsheetApp
      .getActiveSpreadsheet();

  const menu =
    getSheetData(
      spreadsheet,
      SHEETS.MENU
    );

  const blankPriceRows =
    getImageProcessorBlankPriceRows(
      spreadsheet
    );

  return JSON.stringify({

    lang:
      lang,

    menu:
      menu.concat(
        blankPriceRows
      ),

  });

}

// ===========================
// 응답 처리
// ===========================

function getResponseJson(
  lang
) {

  // ==================================
  // 1차 캐시 확인
  //
  // 정상적인 요청 대부분은 여기서 종료.
  // 캐시 HIT에서는 Lock을 사용하지 않는다.
  // ==================================

  const cached =
    getCachedResponse(
      lang
    );

  if (
    cached !== null
  ) {

    return cached;

  }

  // ==================================
  // 캐시 MISS
  //
  // 캐시 생성이 필요한 경우에만 Lock 사용
  // ==================================

  const lock =
    LockService
      .getScriptLock();

  try {

    lock.waitLock(
      10000
    );


    // ==================================
    // Lock 대기 중 다른 요청이
    // 캐시를 생성했을 수 있으므로
    // 다시 확인
    // ==================================

    const cachedAfterLock =
      getCachedResponse(
        lang
      );


    if (
      cachedAfterLock !== null
    ) {

      return cachedAfterLock;

    }


    // ==================================
    // 실제 캐시 생성
    // ==================================

    const spreadsheet =
      SpreadsheetApp
        .getActiveSpreadsheet();


    const data = {

      // 기존 웹사이트 JSON
      // 메뉴판만 기존대로 사용
      menu:
        getSheetData(
          spreadsheet,
          SHEETS.MENU
        ),

      // 기존 안내 JSON
      notice:
        getSheetData(
          spreadsheet,
          SHEETS.NOTICE
        )

    };


    setCachedResponse(
      lang,
      data
    );


    return JSON.stringify({

      lang:
        lang,

      ...data

    });

  } finally {

    lock.releaseLock();

  }

}

// ===========================
// API
// ===========================

function doGet(e) {

  // ==================================
  // 이미지 업데이트 결과 조회
  //
  // /exec?action=updateStatus
  //     &requestId=xxxx
  //
  // 기존 웹사이트 JSON과
  // 별개의 기능
  // ==================================

  const action =
    (
      e &&
      e.parameter &&
      e.parameter.action
    ) || "";

  if (
    action ===
    "imageProcessor"
  ) {

    const lang =
      (
        e &&
        e.parameter &&
        e.parameter.lang
      )
      ||
      LANG.KO;

    return ContentService
      .createTextOutput(
        getImageProcessorResponseJson(
          lang
        )
      )
      .setMimeType(
        ContentService.MimeType.JSON
      );

  }

  if (
    action ===
    "updateStatus"
  ) {

    const requestId =
      (
        e &&
        e.parameter &&
        e.parameter.requestId
      ) || "";


    return jsonResponse(
      getImageUpdateStatus(
        requestId
      )
    );

  }

  // ==================================
  // 기존 웹사이트 API
  // ==================================

  const lang =
    (
      e &&
      e.parameter &&
      e.parameter.lang
    )
    ||
    LANG.KO;

  return ContentService
    .createTextOutput(
      getResponseJson(
        lang
      )
    )
    .setMimeType(
      ContentService.MimeType.JSON
    );

}

// ===========================
// POST API
// ===========================

function doPost(e) {

  try {

    const payload =
      e &&
      e.postData &&
      e.postData.contents
        ? JSON.parse(
            e.postData.contents
          )
        : {};


    if (
      payload.action ===
      "updateImages"
    ) {

      return jsonResponse(
        updateMenuImages(
          payload
        )
      );

    }


    return jsonResponse({

      ok: false,

      error:
        "Unknown action"

    });

  } catch (error) {

    return jsonResponse({

      ok: false,

      error:
        error.message

    });

  }

}

// ===========================
// 트리거
// ===========================

function onSheetEdit(e) {

  if (
    !e ||
    !e.range
  ) {

    return;

  }

  const WATCH_SHEETS = [

    SHEETS.MENU,
    SHEETS.NOTICE,
    SHEETS.PRICE

  ];


  // ==================================
  // Spreadsheet 접근 재시도
  //
  // 간헐적인
  // "Service Spreadsheets failed"
  // 오류 대응
  //
  // 최대 3회 시도
  // 대기: 100ms → 300ms
  // ==================================

  const RETRY_DELAYS = [
    100,
    300
  ];

  let sheetName = null;

  for (
    let attempt = 0;
    attempt <=
      RETRY_DELAYS.length;
    attempt += 1
  ) {

    try {

      sheetName =
        e.range
          .getSheet()
          .getName();

      break;

    } catch (error) {

      if (
        attempt >=
        RETRY_DELAYS.length
      ) {

        console.error(
          "onSheetEdit: " +
          "Spreadsheet access failed after " +
          (attempt + 1) +
          " attempts: " +
          error.message
        );

        return;

      }

      Utilities.sleep(
        RETRY_DELAYS[attempt]
      );

    }

  }


  // ==================================
  // 감시 대상 시트가 아니면 종료
  // ==================================

  if (
    !WATCH_SHEETS.includes(
      sheetName
    )
  ) {

    return;

  }


  // ==================================
  // 마지막 시트 수정 시간 기록
  // ==================================

  PropertiesService
    .getScriptProperties()
    .setProperty(
      PROP_LAST_EDIT,
      Date.now().toString()
    );

}